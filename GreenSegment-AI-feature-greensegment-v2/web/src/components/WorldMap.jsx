import React, { useEffect, useMemo, useRef } from 'react';
import L from 'leaflet';
import { CLUSTER_COLORS } from '../constants.js';

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
}

const GLOBAL_CENTER = [19, 10];
const GLOBAL_ZOOM = 2;
const overviewMarkerRadius = (zoom) => Math.min(4.5, 3.5 + Math.max(0, zoom - GLOBAL_ZOOM) * 0.25);
const OSM_TILES = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
// Local evaluation needs no key. Production must explicitly opt in after domain authentication is configured.
const useStadia = ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname)
  || import.meta.env.VITE_STADIA_MAPS_ENABLED === 'true';

function matchingMarkerPositions(points) {
  const valid = points.filter(({ latitude, longitude }) => Number.isFinite(latitude) && Number.isFinite(longitude)
    && Math.abs(latitude) <= 90 && Math.abs(longitude) <= 180);
  const longitudes = valid.map((point) => point.longitude).sort((a, b) => a - b);
  if (longitudes.length < 2) return valid;

  // Cut the circle at its largest gap so points across ±180° share one map copy.
  let largestGap = longitudes[0] + 360 - longitudes.at(-1);
  let start = longitudes[0];
  for (let i = 1; i < longitudes.length; i += 1) {
    const gap = longitudes[i] - longitudes[i - 1];
    if (gap > largestGap) {
      largestGap = gap;
      start = longitudes[i];
    }
  }
  const center = start + (360 - largestGap) / 2;
  const offset = center >= 180 ? -360 : 0;
  return valid.map((point) => ({ ...point, longitude: point.longitude + (point.longitude < start ? 360 : 0) + offset }));
}

export default function WorldMap({ points = [], onSelectCity, clusterOverlay, viewport, highContrastMarkers = false, fitMatchingPoints = false }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  const overlayRef = useRef(null);
  const navigationRef = useRef(null);
  const callbackRef = useRef(onSelectCity);
  callbackRef.current = onSelectCity;
  const markerColors = CLUSTER_COLORS;
  const markerPoints = useMemo(() => fitMatchingPoints ? matchingMarkerPositions(points) : points, [fitMatchingPoints, points]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const renderer = L.canvas({ padding: 0.5 });
    const redraw = renderer._redraw.bind(renderer);
    // Leaflet can leave an already queued canvas redraw after an animated view reset.
    // Only this map's renderer is guarded; a removed canvas has nothing left to draw.
    renderer._redraw = () => { if (renderer._ctx) redraw(); };
    const map = L.map(containerRef.current, { worldCopyJump: !fitMatchingPoints, zoomControl: false, preferCanvas: true,
      renderer, minZoom: fitMatchingPoints ? 0 : 2, maxZoom: 11 }).setView(GLOBAL_CENTER, GLOBAL_ZOOM);
    L.control.zoom({ position: 'topright' }).addTo(map);
    const tiles = L.tileLayer(useStadia ? 'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png' : OSM_TILES, {
      maxZoom: useStadia ? 20 : 19,
      attribution: useStadia ? '&copy; <a href="https://stadiamaps.com/attribution/">Stadia Maps</a> &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> ' + OSM_ATTRIBUTION : OSM_ATTRIBUTION,
    }).addTo(map);
    const fallback = () => {
      if (!map.hasLayer(tiles)) return;
      map.removeLayer(tiles);
      L.tileLayer(OSM_TILES, { maxZoom: 19, attribution: OSM_ATTRIBUTION }).addTo(map);
    };
    if (useStadia) tiles.once('tileerror', fallback);
    mapRef.current = map;
    layerRef.current = L.layerGroup().addTo(map);
    // Fix map tile sizing after tab navigation/layout updates.
    const frame = requestAnimationFrame(() => map.invalidateSize());
    const resize = new ResizeObserver(() => map.invalidateSize({ pan: false }));
    resize.observe(containerRef.current);
    return () => {
      cancelAnimationFrame(frame); resize.disconnect(); tiles.off('tileerror', fallback);
      map.stop();
      // Leaflet 1.9's delayed zoom completion must finish before its pane is removed.
      if (map._animatingZoom) map._onZoomTransitionEnd();
      // Remove paths while their canvas still exists, before map.remove destroys the renderer.
      layerRef.current?.clearLayers();
      map.remove();
      mapRef.current = null; layerRef.current = null; navigationRef.current = null;
    };
  }, [fitMatchingPoints]);

  useEffect(() => {
    const layer = layerRef.current;
    const map = mapRef.current;
    if (!layer || !map) return;
    layer.clearLayers();
    const renderer = map.options.renderer;
    let hovered = null;
    const radius = () => overviewMarkerRadius(map.getZoom());
    for (const point of markerPoints) {
      const color = markerColors[point.cluster_id] || '#64748b';
      const circle = L.circleMarker([point.latitude, point.longitude], {
        radius: highContrastMarkers ? radius() : 3.2,
        color: highContrastMarkers ? '#ffffff' : color, fillColor: color,
        weight: highContrastMarkers ? 0.65 : 0.35,
        fillOpacity: highContrastMarkers ? 1 : 0.78,
        opacity: highContrastMarkers ? 1 : 0.9, renderer,
      });
      circle.bindTooltip(`<strong>${escapeHTML(point.city_name)}</strong><br/>${escapeHTML(point.country_name)} · Cụm ${point.cluster_id}`,
        { sticky: true, direction: 'top', opacity: 0.98 });
      circle.on('click', () => callbackRef.current?.(point.city_id));
      if (highContrastMarkers) circle.on({
        mouseover: () => {
          hovered = circle;
          circle.setRadius(radius() + 1.5).setStyle({ weight: 1.3 });
          circle.bringToFront();
        },
        mouseout: () => {
          hovered = null;
          circle.setRadius(radius()).setStyle({ weight: 0.65 });
        },
      });
      circle.addTo(layer);
    }
    // Update the existing canvas markers only when a zoom finishes; no React state or animation loop.
    const updateSizes = () => layer.eachLayer((circle) => circle.setRadius(radius() + (circle === hovered ? 1.5 : 0)));
    if (highContrastMarkers) map.on('zoomend', updateSizes);
    return () => {
      map.off('zoomend', updateSizes);
      layer.clearLayers();
    };
  }, [markerPoints, highContrastMarkers]);

  useEffect(() => {
    const map = mapRef.current;
    if (!fitMatchingPoints || !map || !markerPoints.length) return;
    map.invalidateSize({ pan: false });
    const bounds = L.latLngBounds(markerPoints.map(({ latitude, longitude }) => [latitude, longitude]));
    // The footer attribution and zoom controls need more room on the right.
    map.fitBounds(bounds, { paddingTopLeft: [20, 20], paddingBottomRight: [32, 28], maxZoom: 8, animate: false });
  }, [fitMatchingPoints, markerPoints]);

  // Overview keeps separate viewport rules for its filter and reset controls.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !viewport) return;
    const previous = navigationRef.current;
    navigationRef.current = { ...previous, country: viewport.country, resetVersion: viewport.resetVersion };
    const reset = previous && previous.resetVersion !== viewport.resetVersion;
    const clearedCountry = previous?.country && !viewport.country;
    if (reset || clearedCountry) {
      map.stop();
      map.setView(GLOBAL_CENTER, GLOBAL_ZOOM, { animate: false });
      navigationRef.current.focusKey = null;
      return;
    }
    // A global cluster/sector change updates markers without interrupting exploration.
    if (!viewport.country || !viewport.ready || previous?.focusKey === viewport.filterKey) return;
    navigationRef.current.focusKey = viewport.filterKey;
    const coordinates = points.filter((point) => Number.isFinite(point.latitude) && Number.isFinite(point.longitude)
      && Math.abs(point.latitude) <= 90 && Math.abs(point.longitude) <= 180)
      .map((point) => [point.latitude, point.longitude]);
    if (!coordinates.length) return;
    const bounds = L.latLngBounds(coordinates);
    const size = map.getSize();
    const overlay = overlayRef.current;
    const topBand = overlay && overlay.offsetWidth > size.x * 0.55;
    // Reserve the cards' actual footprint; on mobile they form a compact top band.
    const paddingTopLeft = topBand ? [20, (overlay.offsetHeight || 112) + overlay.offsetTop + 18]
      : [(overlay?.offsetWidth || 0) + (overlay?.offsetLeft || 0) + 20, 24];
    map.stop();
    map.fitBounds(bounds, {
      paddingTopLeft, paddingBottomRight: [28, 24], maxZoom: 8,
      animate: !window.matchMedia('(prefers-reduced-motion: reduce)').matches, duration: 0.3,
    });
  }, [points, viewport]);

  return <div className="worldmap-wrap">
    <div className="worldmap" ref={containerRef} role="region" aria-label="Bản đồ các đô thị toàn cầu"/>
    {clusterOverlay && <div className="map-cluster-overlay" ref={overlayRef}>{clusterOverlay}</div>}
    <div className="map-legend">
      <span><i style={{ background: markerColors[0] }}/> Dân cư · Giao thông</span>
      <span><i style={{ background: markerColors[1] }}/> Công nghiệp</span>
      <span><i style={{ background: markerColors[2] }}/> Năng lượng</span>
    </div>
  </div>;
}
