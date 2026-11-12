import React, { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Sparkles } from 'lucide-react';
import { apiGet, apiPost } from '../api.js';
import { SECTOR_LABELS, SECTOR_COLORS, num, pct, topSectors } from '../constants.js';
import { ClusterStackedChart } from '../components/SectorCharts.jsx';
import { ErrorBox, Loading, Panel } from '../components/UI.jsx';

export default function ClusterExplorer({ selectedClusterId: selected = 0, onSelectCluster, mapClusterId = '' }) {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const [reports, setReports] = useState({});
  const [aiError, setAiError] = useState('');
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const request = useRef(null);
  useEffect(() => {
    const controller = new AbortController();
    setError('');
    apiGet('/cluster-explorer', {}, { signal: controller.signal }).then(setStats)
      .catch((e) => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, [refresh]);
  useEffect(() => {
    setBusy(false); setAiError('');
    return () => { request.current?.abort(); request.current = null; };
  }, [selected]);
  async function analyze() {
    const controller = new AbortController();
    request.current = controller;
    setBusy(true); setAiError('');
    try {
      const result = await apiPost(`/cluster-explorer/${selected}/interpret`, {}, { signal: controller.signal });
      if (!controller.signal.aborted) setReports((prev) => ({ ...prev, [selected]: result }));
    } catch (e) { if (!controller.signal.aborted) setAiError(e.message); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  const cluster = stats?.clusters.find((c) => c.cluster_id === selected);
  const report = reports[selected]?.report;
  const highlights = cluster ? topSectors(cluster.centroid_percent, 3) : [];

  return <section className="cluster-explorer overview-clusters" aria-labelledby="cluster-exploration-title">
    <header className="ce-section-heading">
      <h2 id="cluster-exploration-title">Khám phá các cụm đô thị</h2>
      <p>So sánh đặc điểm cơ cấu phát thải của ba cụm đô thị dựa trên toàn bộ dữ liệu nghiên cứu, độc lập với các bộ lọc trên bản đồ.</p>
    </header>
    {error && <><ErrorBox message={error}/><button className="button button-outline" onClick={() => setRefresh((n) => n + 1)}>Tải lại dữ liệu</button></>}
    {!stats && !error && <Loading/>}
    {cluster && <>
      <p className="ce-scope overview-analysis-status" aria-live="polite">Hồ sơ đang phân tích: <strong>Cụm {selected} – {cluster.short_name}</strong>.</p>
      <div className="ce-exploration-grid">
        <Panel className="ce-overview-chart" title="So sánh cơ cấu GHG của ba cụm" subtitle="Cơ cấu phát thải tại tâm K-Means của từng cụm, thể hiện tỷ trọng 7 lĩnh vực với tổng bằng 100%.">
          <details className="overview-help overview-chart-help">
            <summary>Hiểu GHG, cơ cấu phát thải và tâm K-Means</summary>
            <dl>
              <dt>GHG</dt><dd>GHG là viết tắt của Greenhouse Gases, nghĩa là khí nhà kính.</dd>
              <dt>Cơ cấu phát thải</dt><dd>Tỷ lệ đóng góp của từng lĩnh vực vào tổng lượng phát thải khí nhà kính của một đô thị hoặc trong cơ cấu tham chiếu của một cụm.</dd>
              <dt>Tâm cụm K-Means</dt><dd>Điểm trung tâm do mô hình K-Means tính toán trong không gian bảy tỷ trọng phát thải. Đây không phải dữ liệu của một đô thị cụ thể và có thể chênh lệch nhẹ so với trung bình của các đô thị được gán vào cụm.</dd>
            </dl>
          </details>
          <ClusterStackedChart clusters={stats.clusters} basis="centroid" selectedClusterId={selected} onSelectCluster={onSelectCluster}/>
          <p className="ce-chart-hint">Chọn một cụm trên biểu đồ để cập nhật bản đồ và xem hồ sơ phân tích chi tiết của cụm.</p>
        </Panel>
        <Panel className="ce-cluster-profile" title={<><span className="ce-profile-id" style={{ color: cluster.color }}>Cụm {selected}</span><span className="ce-profile-name">{cluster.short_name}</span></>}>
          <dl className="ce-profile-kpis">
            <div><dt>Số đô thị trong cụm</dt><dd>{num(cluster.city_count)}</dd></div>
            <div><dt>Tỷ lệ trong toàn bộ dữ liệu</dt><dd>{pct(cluster.city_percentage, 2)}</dd></div>
          </dl>
          <h3 className="ce-profile-subheading">Ba lĩnh vực nổi bật tại tâm K-Means</h3>
          <ul className="ce-highlights">{highlights.map((sector) => <li key={sector}>
            <div className="ce-highlight-heading"><span>{SECTOR_LABELS[sector]}</span><strong>{pct(cluster.centroid_percent[sector], 2)}</strong></div>
            <div className="progress-track" role="progressbar" aria-label={SECTOR_LABELS[sector]} aria-valuenow={cluster.centroid_percent[sector]} aria-valuemin={0} aria-valuemax={100}>
              <div style={{ background: SECTOR_COLORS[sector], width: `${cluster.centroid_percent[sector]}%` }}/>
            </div>
          </li>)}</ul>
          <p className="ce-profile-scope">Quy mô trên toàn bộ {num(stats.total_cities)} đô thị.</p>
        </Panel>
      </div>
      <Panel title={<><Sparkles size={20}/> Gemini diễn giải cụm</>}>
        <div className="ce-ai-action"><p>Gemini hỗ trợ diễn giải đặc điểm cơ cấu phát thải và sự khác biệt giữa các cụm dựa trên số liệu thống kê của hệ thống.</p>
          <button className="button button-primary" disabled={busy} onClick={analyze}><Sparkles size={16}/>{busy ? 'Đang phân tích…' : 'Gemini diễn giải cụm'}</button></div>
        {busy && <Loading text={`Gemini đang diễn giải cụm ${selected}…`}/>}
        {aiError && <ErrorBox message={aiError}/>}
        <div aria-live="polite">{report ? <article className="ce-report">
          <p className="ce-scope">Diễn giải cho Cụm {selected} · Nội dung AI cần được đối chiếu với dữ liệu.</p>
          <h3>Đặc điểm nổi bật</h3><p>{report.summary}</p>
          <h3>So sánh các cụm</h3><ul>{report.comparisons.map((v, i) => <li key={i}>{v}</li>)}</ul>
          <h3>Mức độ tương đồng trong cụm</h3><p>{report.dispersion_and_representativeness}</p>
          <h3>Hạn chế và hướng nghiên cứu</h3><ul>{report.limitations.map((v, i) => <li key={`limit-${i}`}>{v}</li>)}</ul>
          <ul>{report.research_questions.map((v, i) => <li key={`research-${i}`}>{v}</li>)}</ul>
        </article> : !busy && <div className="ce-scope overview-report-empty">
          <p>Chưa có báo cáo phân tích cho cụm này.</p>
          <p>Nhấn "Gemini diễn giải cụm" để tạo báo cáo.</p>
        </div>}</div>
      </Panel>
      <aside className="data-note overview-methodology" aria-label="Phương pháp và giới hạn nghiên cứu">
        <AlertTriangle size={15} aria-hidden="true"/>
        <div>
          <p>Nguồn dữ liệu: EDGAR 2024. Các đô thị được phân thành 3 cụm bằng thuật toán K-Means, dựa trên tỷ trọng phát thải khí nhà kính của 7 lĩnh vực.</p>
          <p>Kết quả phản ánh đặc điểm cơ cấu phát thải, không đủ cơ sở để kết luận nguyên nhân phát thải hoặc tính khả thi của các giải pháp công nghệ.</p>
          <details className="overview-help">
            <summary>Về nguồn dữ liệu EDGAR</summary>
            <p>EDGAR là cơ sở dữ liệu phát thải được sử dụng trong nghiên cứu, cung cấp số liệu phát thải khí nhà kính năm 2024 của dự án.</p>
          </details>
        </div>
      </aside>
    </>}
  </section>;
}
