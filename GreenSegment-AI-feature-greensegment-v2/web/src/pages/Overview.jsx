import React, { useEffect, useMemo, useState } from 'react';
import { Building2, Check, Globe2, Layers3, MapPinned, Network, RefreshCw } from 'lucide-react';
import { apiGet } from '../api.js';
import { num, pct, SECTOR_LABELS, shortClusterName } from '../constants.js';
import ClusterExplorer from './ClusterExplorer.jsx';
import WorldMap from '../components/WorldMap.jsx';
import DataFilters from '../components/DataFilters.jsx';
import { Empty, ErrorBox, Loading, Panel } from '../components/UI.jsx';

const EMPTY_POINTS = [];

export default function Overview({ filters, analysisClusterId, mapResetVersion, onFilter, countries, onSelectCity }) {
  const [stats, setStats] = useState(null);
  const [mapData, setMapData] = useState(null);
  const [error, setError] = useState('');
  const [mapError, setMapError] = useState('');
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const filterKey = JSON.stringify([filters.country, filters.cluster_id, filters.sector]);
  const currentMapData = mapData?.filterKey === filterKey ? mapData : null;
  const viewport = useMemo(() => ({ country: filters.country, filterKey, resetVersion: mapResetVersion, ready: !!currentMapData }),
    [filters.country, filterKey, mapResetVersion, !!currentMapData]);
  const selected = {
    country: filters.country,
    cluster_id: filters.cluster_id === '' ? undefined : Number(filters.cluster_id),
    sector: filters.sector,
  };
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setMapError('');
    apiGet('/overview', selected, { signal: controller.signal })
      .then((result) => { if (!controller.signal.aborted) setStats(result); })
      .catch((e) => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    apiGet('/cities/map', { ...selected, limit: 5000 }, { signal: controller.signal })
      .then((result) => { if (!controller.signal.aborted) setMapData({ ...result, filterKey }); })
      .catch((e) => { if (!controller.signal.aborted) setMapError(e.message); });
    return () => controller.abort();
  }, [filters.country, filters.cluster_id, filters.sector, refresh]);

  const isFiltered = !!(filters.country || filters.cluster_id !== '' || filters.sector);
  const selectCluster = (id) => onFilter('cluster_id', String(id));
  const mapContext = [filters.country || 'Toàn cầu', filters.cluster_id === '' ? 'Tất cả 3 cụm'
    : `Cụm ${filters.cluster_id} – ${shortClusterName[filters.cluster_id]}`,
    filters.sector ? `Tỷ trọng cao nhất: ${SECTOR_LABELS[filters.sector]}` : null].filter(Boolean).join(' · ');
  const clusterSelector = stats && <div className="ce-selector" role="group" aria-label="Lọc cụm trên bản đồ">
    <button type="button" aria-pressed={filters.cluster_id === ''} onClick={() => selectCluster('')}
      className={filters.cluster_id === '' ? 'selected' : ''} style={{ '--cluster-color': '#087e67' }}>
      <span><strong>Tất cả 3 cụm</strong></span><Check className="map-selection-check" size={16} aria-hidden="true"/>
    </button>
    {stats.clusters.map((cluster) => <button key={cluster.cluster_id} type="button"
      aria-pressed={String(filters.cluster_id) === String(cluster.cluster_id)}
      aria-label={`Cụm ${cluster.cluster_id} – ${cluster.short_name}. Lọc bản đồ và chọn hồ sơ cụm. Quy mô toàn bộ cụm: ${num(cluster.city_count)} đô thị.`}
      title={`Cụm ${cluster.cluster_id} – ${cluster.short_name}`}
      className={String(filters.cluster_id) === String(cluster.cluster_id) ? 'selected' : ''}
      style={{ '--cluster-color': cluster.color }} onClick={() => selectCluster(cluster.cluster_id)}>
      <span><small className="ce-cluster-label">Cụm {cluster.cluster_id}</small><strong>{cluster.short_name}</strong>
        <small className="ce-cluster-size">{num(cluster.city_count)} đô thị · {pct(cluster.city_percentage, 2)} toàn bộ dữ liệu</small></span>
      <Check className="map-selection-check" size={16} aria-hidden="true"/>
    </button>)}
  </div>;

  return <div className="page-enter overview-page">
    <div className="page-intro">
      <div><h1>Bức tranh phát thải đô thị toàn cầu</h1>
        <p>Khám phá đặc điểm cơ cấu phát thải khí nhà kính của các đô thị trên thế giới.</p>
      </div>
    </div>
    <DataFilters filters={filters} onFilter={onFilter} countries={countries} inline
      clusterHelp={<details className="overview-help">
        <summary>Cụm phát thải là gì?</summary>
        <p>Một nhóm đô thị có cơ cấu tỷ trọng phát thải giữa các lĩnh vực tương đồng, được xác định bằng thuật toán phân cụm.</p>
      </details>}/>
    {error && <ErrorBox message={error} />}
    {loading && !stats ? <Loading/> : stats && <>
      <div className="stat-grid" aria-busy={loading}>
        <div className="stat-card"><div className="stat-icon green"><Building2 size={23}/></div><span>Số đô thị {isFiltered ? 'phù hợp' : 'toàn cầu'}</span>
          <strong>{loading ? '…' : num(stats.filtered_cities)}</strong><small>{isFiltered ? `trên ${num(stats.total_cities)} đô thị` : 'Trong bộ dữ liệu nghiên cứu'}</small></div>
        <div className="stat-card"><div className="stat-icon blue"><Globe2 size={23}/></div><span>Quốc gia / vùng lãnh thổ</span>
          <strong>{num(stats.total_countries)}</strong><small>Trong toàn bộ dữ liệu</small></div>
        <div className="stat-card"><div className="stat-icon orange"><Layers3 size={23}/></div><span>Số cụm phát thải</span>
          <strong>{num(stats.total_clusters)}</strong><small>K-Means · K = 3</small></div>
        <div className="stat-card"><div className="stat-icon purple"><Network size={23}/></div><span>Đặc trưng phân nhóm</span>
          <strong>07</strong><small>Lĩnh vực phát thải GHG</small></div>
      </div>
        <Panel title={<><MapPinned size={20}/> Bản đồ phân cụm đô thị</>} subtitle={mapContext} className="map-panel"
          action={<button type="button" className="icon-button" title="Tải lại" aria-label="Tải lại bản đồ" onClick={() => setRefresh((n) => n + 1)}><RefreshCw size={17}/></button>}>
          {mapError && <ErrorBox message={mapError} />}
          <div className="ce-scope overview-map-instructions">
            <p>Bản đồ và số đô thị phù hợp sẽ thay đổi theo bộ lọc đã chọn.</p>
            <p>Khi chọn Cụm 0, 1 hoặc 2 trên bản đồ, hệ thống đồng thời cập nhật kết quả lọc và hồ sơ phân tích của cụm tương ứng.</p>
          </div>
          <WorldMap points={currentMapData?.points ?? EMPTY_POINTS} onSelectCity={onSelectCity}
            clusterOverlay={clusterSelector} viewport={viewport} highContrastMarkers/>
          {!mapError && currentMapData?.total_matching === 0 && <Empty>Không có đô thị có tọa độ hợp lệ thỏa bộ lọc. Hãy điều chỉnh bộ lọc phía trên.</Empty>}
          <p className="overview-map-card-scope">Số lượng và tỷ lệ trên các thẻ cụm được tính từ toàn bộ dữ liệu, không chỉ từ các đô thị đang hiển thị trên bản đồ.</p>
          <div className="map-caption overview-map-caption" role="status">
            {mapError ? <p>Không tải được điểm đô thị. Hãy thử tải lại bản đồ.</p> : !currentMapData
              ? <p>Đang tải điểm đô thị...</p> : <>
                {currentMapData.shown > 0 && <p>{currentMapData.sampled
                  ? `Đang hiển thị ${num(currentMapData.shown)} trong số ${num(currentMapData.total_matching)} đô thị có tọa độ hợp lệ.`
                  : `Đang hiển thị đầy đủ ${num(currentMapData.shown)} đô thị phù hợp có tọa độ hợp lệ.`}</p>}
                {!loading && stats.filtered_cities !== currentMapData.total_matching
                  && <p>Tổng số đô thị phù hợp bộ lọc: {num(stats.filtered_cities)}.</p>}
                {currentMapData.sampled && <p>Bản đồ lấy mẫu tối đa 5.000 điểm để tối ưu hiệu năng hiển thị.</p>}
                {currentMapData.shown > 0 && <p>Nhấn vào một điểm để xem hồ sơ đô thị.</p>}
              </>}
          </div>
          <p className="map-caption overview-map-background-note">Nền bản đồ cần kết nối Internet.</p>
        </Panel>
    </>}
    <ClusterExplorer selectedClusterId={analysisClusterId} onSelectCluster={selectCluster} mapClusterId={filters.cluster_id}/>
  </div>;
}
