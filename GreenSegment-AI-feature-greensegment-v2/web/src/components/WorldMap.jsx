import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { CLUSTER_COLORS } from '../constants.js';

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
}

const GLOBAL_CENTER = [19, 10];
const GLOBAL_ZOOM = 2;
const OVERVIEW_MARKER_COLORS = { 0: '#2563eb', 1: '#d97706', 2: '#047857' };
const overviewMarkerRadius = (zoom) => Math.min(4.5, 3.5 + Math.max(0, zoom - GLOBAL_ZOOM) * 0.25);

export default function WorldMap({ points = [], onSelectCity, clusterOverlay, viewport, highContrastMarkers = false }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  const overlayRef = useRef(null);
  const navigationRef = useRef(null);
  const callbackRef = useRef(onSelectCity);
  callbackRef.current = onSelectCity;
  const markerColors = highContrastMarkers ? OVERVIEW_MARKER_COLORS : CLUSTER_COLORS;

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, { worldCopyJump: true, zoomControl: false, preferCanvas: true,
      renderer: L.canvas({ padding: 0.5 }), minZoom: 2, maxZoom: 11 }).setView(GLOBAL_CENTER, GLOBAL_ZOOM);
    L.control.zoom({ position: 'topright' }).addTo(map);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);
    mapRef.current = map;
    layerRef.current = L.layerGroup().addTo(map);
    // Fix map tile sizing after tab navigation/layout updates.
    const frame = requestAnimationFrame(() => map.invalidateSize());
    const resize = new ResizeObserver(() => map.invalidateSize({ pan: false }));
    resize.observe(containerRef.current);
    return () => {
      cancelAnimationFrame(frame); resize.disconnect(); map.remove();
      mapRef.current = null; layerRef.current = null; navigationRef.current = null;
    };
  }, []);

  useEffect(() => {
    const layer = layerRef.current;
    const map = mapRef.current;
    if (!layer || !map) return;
    layer.clearLayers();
    const renderer = map.options.renderer;
    let hovered = null;
    const radius = () => overviewMarkerRadius(map.getZoom());
    for (const point of points) {
      const color = markerColors[point.cluster_id] || '#64748b';
      const circle = L.circleMarker([point.latitude, point.longitude], {
        radius: highContrastMarkers ? radius() : 3.2,
        color: highContrastMarkers ? '#ffffff' : color, fillColor: color,
        weight: highContrastMarkers ? 1.2 : 0.35,
        fillOpacity: highContrastMarkers ? 1 : 0.78,
        opacity: highContrastMarkers ? 1 : 0.9, renderer,
      });
      circle.bindTooltip(`<strong>${escapeHTML(point.city_name)}</strong><br/>${escapeHTML(point.country_name)} · Cụm ${point.cluster_id}`,
        { sticky: true, direction: 'top', opacity: 0.98 });
      circle.on('click', () => callbackRef.current?.(point.city_id));
      if (highContrastMarkers) circle.on({
        mouseover: () => {
          hovered = circle;
          circle.setRadius(radius() + 1.5).setStyle({ weight: 1.8 });
          circle.bringToFront();
        },
        mouseout: () => {
          hovered = null;
          circle.setRadius(radius()).setStyle({ weight: 1.2 });
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
  }, [points, highContrastMarkers]);

  // Overview opts in. Other consumers (including Market Explorer) retain their viewport.
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
