import React, { useId, useState } from 'react';
import { Check, ChevronDown, ChevronUp } from 'lucide-react';
import { CLUSTER_COLORS, num } from '../constants.js';

export default function MapClusterSelector({ clusters, selectedId, onSelect }) {
  const [expanded, setExpanded] = useState(false);
  const optionsId = useId();
  const all = selectedId === '';

  return <section className="map-selector" data-expanded={expanded} aria-label="Chọn cụm phát thải">
    <h3><button className="map-selector-toggle" type="button" aria-controls={optionsId} aria-expanded={expanded}
      aria-label={expanded ? 'Thu gọn bộ chọn cụm' : 'Mở bộ chọn cụm'} onClick={() => setExpanded(!expanded)}>
      <span>Chọn cụm</span>{expanded ? <ChevronUp size={17} aria-hidden="true"/> : <ChevronDown size={17} aria-hidden="true"/>}
    </button></h3>
    {!expanded && <p className="map-selector-summary" role="status">Đang xem: {all ? 'Tất cả 3 cụm' : `Cụm ${selectedId}`}</p>}
    <div id={optionsId} className="ce-selector" role="group" aria-label="Lọc cụm trên bản đồ" hidden={!expanded}>
      <button type="button" aria-pressed={all} onClick={() => onSelect('')}
        className={all ? 'selected' : ''} style={{ '--cluster-color': 'var(--accent)' }}>
        <span><strong>Tất cả 3 cụm</strong></span><Check className="map-selection-check" size={16} aria-hidden="true"/>
      </button>
      {clusters.map((cluster) => {
        const active = String(selectedId) === String(cluster.cluster_id);
        const name = cluster.cluster_id === 0 ? 'Dân cư - Giao thông' : cluster.short_name;
        return <button key={cluster.cluster_id} type="button" aria-pressed={active}
          aria-label={`Cụm ${cluster.cluster_id} – ${name}. Lọc bản đồ và chọn hồ sơ cụm.${active ? ` Quy mô toàn bộ cụm: ${num(cluster.city_count)} đô thị.` : ''}`}
          className={active ? 'selected' : ''} style={{ '--cluster-color': CLUSTER_COLORS[cluster.cluster_id] }}
          onClick={() => onSelect(cluster.cluster_id)}>
          <span><small className="ce-cluster-label">Cụm {cluster.cluster_id}</small><strong>{name}</strong>
            {active && <small className="ce-cluster-size">{num(cluster.city_count)} đô thị</small>}</span>
          <Check className="map-selection-check" size={16} aria-hidden="true"/>
        </button>;
      })}
    </div>
  </section>;
}
