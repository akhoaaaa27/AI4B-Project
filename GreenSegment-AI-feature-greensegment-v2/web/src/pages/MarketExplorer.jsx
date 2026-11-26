import React, { useEffect, useRef, useState } from 'react';
import { ArrowUpDown, Building2, Download, FileText, Globe2, Layers3, Search, SlidersHorizontal, Sparkles, Telescope } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, Text } from 'recharts';
import { apiPost } from '../api.js';
import { CLUSTER_COLORS, SECTORS, SECTOR_LABELS, num, pct } from '../constants.js';
import { compactGhg, fullGhg } from '../ghgFormatting.js';
import CityGhgValue from '../components/CityGhgValue.jsx';
import { Empty, ErrorBox, Loading, Note, Panel } from '../components/UI.jsx';
import WorldMap from '../components/WorldMap.jsx';

const EXAMPLE = 'Tôi kinh doanh công nghệ thu hồi nhiệt thải công nghiệp. Hãy tìm 10 đô thị ở Nhật Bản có tỷ trọng phát thải công nghiệp từ 30% trở lên, ưu tiên đô thị có lượng GHG công nghiệp lớn nhất.';
const INITIAL_QUERY = { sector: 'industry', countries: [], cluster_id: null, min_sector_share_percent: null,
  max_sector_share_percent: null, sort_by: 'sector_emissions', sort_order: 'desc', limit: 10 };
const SORT_LABELS = { sector_share: 'Tỷ trọng lĩnh vực', sector_emissions: 'GHG lĩnh vực', total_ghg: 'Tổng GHG đô thị' };
const sectorName = (sector) => sector === 'all' ? 'Tất cả lĩnh vực' : SECTOR_LABELS[sector];
const thresholdText = (value) => `${value.toLocaleString('vi-VN', { maximumSignificantDigits: 21 })}%`;

function sortLabel(query) {
  if (query.sort_by === 'sector_share') return `Tỷ trọng ${sectorName(query.sector)}`;
  if (query.sort_by === 'sector_emissions') return `GHG ${sectorName(query.sector)}`;
  return SORT_LABELS.total_ghg;
}

function AppliedConditions({ query, context }) {
  const fields = [
    ['Quốc gia', query.countries.join(', ') || 'Tất cả quốc gia'],
    ['Lĩnh vực phát thải', sectorName(query.sector)],
    ['Cụm đô thị', query.cluster_id == null ? 'Tất cả 3 cụm' : `Cụm ${query.cluster_id}`],
    ['Tỷ trọng tối thiểu', query.min_sector_share_percent == null ? 'Không giới hạn' : thresholdText(query.min_sector_share_percent)],
    ['Sắp xếp', `${sortLabel(query)} ${query.sort_order === 'desc' ? 'giảm' : 'tăng'} dần`],
    ['Số kết quả hiển thị', `Top ${query.limit}`],
  ];
  if (query.max_sector_share_percent != null) fields.push(['Tỷ trọng tối đa', thresholdText(query.max_sector_share_percent)]);

  const general = context?.sector_basis === 'general_exploration';
  const mapped = context?.sector_basis === 'product_mapping';
  return <Panel title={<><SlidersHorizontal size={18}/> Điều kiện áp dụng</>} className="market-applied">
    <dl className="market-applied-fields">{fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    {(context?.product || context?.business_goal || general || mapped) && <div className="market-research-context">
      <h3>BỐI CẢNH NGHIÊN CỨU</h3>
      {context.product && <p className="market-context-product">{context.product}</p>}
      {context.business_goal && <p>Mục tiêu: {context.business_goal}</p>}
      {general && <p>Khám phá chung theo tổng GHG. Bạn có thể chọn thêm lĩnh vực trong chế độ bộ lọc. Kết quả không xác nhận nhu cầu mua sản phẩm.</p>}
      {mapped && <p>Lĩnh vực là giả định từ sản phẩm/công nghệ; cần đối chiếu tiêu chí nghiên cứu, không suy ra nhu cầu mua.</p>}
    </div>}
  </Panel>;
}

function TopSubsetSummary({ summary, count }) {
  return <div className="market-top-summary">
    <div className="market-top-heading"><h3>Thống kê riêng Top {num(count)}</h3><span>{num(count)} đô thị</span></div>
    <dl className="market-top-values">
      <div><dt>Quốc gia</dt><dd>{num(summary.country_count)}</dd></div>
      <div><dt>Tỷ trọng trung bình</dt><dd>{summary.mean_sector_share_percent == null ? '—' : pct(summary.mean_sector_share_percent, 2)}</dd></div>
    </dl>
    <div className="market-cluster-counts market-top-clusters">{[0, 1, 2].map((id) => <span key={id}>
      <i className="market-cluster-dot" style={{ background: CLUSTER_COLORS[id] }} aria-hidden="true"/>Cụm {id}: <strong>{num(summary.cluster_counts[id])}</strong>
    </span>)}</div>
  </div>;
}

function RankingTick({ x, y, payload, labelWidth }) {
  return <Text x={x} y={y} width={labelWidth} maxLines={2} textAnchor="end" verticalAnchor="middle"
    style={{ fontSize: 11 }} fill="var(--text-secondary)">{payload.value}</Text>;
}

function RankingChart({ query, items }) {
  const [plotWidth, setPlotWidth] = useState(0);
  const narrow = plotWidth > 0 && plotWidth < 460;
  const labelAxisWidth = narrow ? 112 : 166;
  const subset = `Top ${num(items.length)} đô thị`;
  const sector = sectorName(query.sector);
  const share = query.sort_by === 'sector_share';
  const ascending = query.sort_order === 'asc' ? ' tăng dần' : '';
  const title = share ? `Tỷ trọng phát thải ${sector} của ${subset}`
    : `${subset} theo ${query.sort_by === 'total_ghg' ? 'tổng GHG' : `phát thải ${sector}`}${ascending}`;
  const rows = items.map((city, i) => ({ ...city, label: `${i + 1}. ${city.city_name}`, value: {
    sector_share: city.sector_share_percent, sector_emissions: city.sector_emissions, total_ghg: city.ghg_total_2024,
  }[query.sort_by] }));

  return <Panel title={title} subtitle={share ? 'Đơn vị: % · Không phải điểm tiềm năng' : 'Đơn vị: tấn/năm'} className="market-ranking-panel">
    <div className="market-ranking-scroll" role="region" aria-label="Biểu đồ xếp hạng đô thị" tabIndex={0}>
      <div className="market-ranking-plot" style={{ height: Math.max(112, rows.length * 36 + 36) }}>
        <ResponsiveContainer width="100%" height="100%" onResize={(width) => setPlotWidth(width)}>
          <BarChart data={rows} layout="vertical" margin={{ left: 0, right: 34, top: 6, bottom: 4 }}>
            <CartesianGrid horizontal={false} strokeDasharray="3 5"/>
            <XAxis type="number" tickCount={narrow ? 3 : 4} minTickGap={14} tickFormatter={share ? (value) => pct(value, 0) : compactGhg} tick={{ fontSize: 10 }}/>
            <YAxis type="category" dataKey="label" width={labelAxisWidth} interval={0} tick={<RankingTick labelWidth={labelAxisWidth - 16}/>}/>
            <Tooltip formatter={(value) => [share ? pct(value, 2) : fullGhg(value), sortLabel(query)]}
              labelFormatter={(_, payload) => payload?.[0]?.payload ? `${payload[0].payload.city_name} · ${payload[0].payload.country_name}` : ''}/>
            <Bar dataKey="value" maxBarSize={19} radius={[0, 4, 4, 0]} fill="var(--accent)"/>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  </Panel>;
}

export default function MarketExplorer({ countries, onSelectCity }) {
  const [text, setText] = useState('');
  const [mode, setMode] = useState('ai');
  const [draft, setDraft] = useState(INITIAL_QUERY);
  const [parsed, setParsed] = useState(null);
  const [result, setResult] = useState(null);
  const [report, setReport] = useState(null);
  const [confirmedText, setConfirmedText] = useState('');
  const [busy, setBusy] = useState({});
  const [errors, setErrors] = useState({});
  const controllers = useRef({});
  useEffect(() => () => Object.values(controllers.current).forEach((c) => c.abort()), []);

  function stop(kind) {
    controllers.current[kind]?.abort();
    delete controllers.current[kind];
    setBusy((prev) => ({ ...prev, [kind]: false }));
  }
  async function run(kind, route, payload, onSuccess) {
    controllers.current[kind]?.abort();
    const controller = new AbortController();
    controllers.current[kind] = controller;
    setBusy((prev) => ({ ...prev, [kind]: true }));
    setErrors((prev) => ({ ...prev, [kind]: '' }));
    try {
      const response = await apiPost(route, payload, { signal: controller.signal });
      if (!controller.signal.aborted) onSuccess(response);
    } catch (e) { if (!controller.signal.aborted) setErrors((prev) => ({ ...prev, [kind]: e.message })); }
    finally { if (!controller.signal.aborted) setBusy((prev) => ({ ...prev, [kind]: false })); }
  }
  function invalidate() {
    ['parse', 'search', 'report', 'export'].forEach(stop);
    setResult(null); setReport(null); setConfirmedText(''); setErrors({});
  }
  function edit(key, value) {
    invalidate();
    setDraft((prev) => {
      const next = { ...prev, [key]: value };
      if (key === 'sector' && value === 'all') Object.assign(next, {
        min_sector_share_percent: null, max_sector_share_percent: null, sort_by: 'total_ghg',
      });
      return next;
    });
  }
  function changeText(value) {
    invalidate(); setText(value); setParsed(null);
  }
  function changeMode(next) {
    if (next === mode) return;
    invalidate(); setParsed(null); setMode(next);
  }
  function parse() {
    invalidate(); setParsed(null);
    const requestText = text.trim();
    run('parse', '/market/parse', { text: requestText }, (response) => {
      setParsed(response);
      if (!response.unsupported_criteria.length) search(response.query, requestText);
    });
  }
  function search(query = draft, requestText = '') {
    stop('report'); stop('export'); setReport(null); setResult(null);
    setErrors((prev) => ({ ...prev, report: '', export: '' }));
    run('search', '/market/search', query, (response) => { setResult(response); setConfirmedText(requestText); });
  }
  function manualSearch(event) {
    event.preventDefault();
    const threshold = draft.min_sector_share_percent;
    if (threshold != null && (!Number.isFinite(threshold) || threshold < 0 || threshold > 100)) {
      setErrors((prev) => ({ ...prev, search: 'Tỷ trọng phải là số từ 0 đến 100%.' })); return;
    }
    if (![5, 10, 20, 50].includes(draft.limit)) {
      setErrors((prev) => ({ ...prev, search: 'Hãy chọn Top 5, 10, 20 hoặc 50.' })); return;
    }
    search(draft);
  }
  function sort(field) {
    const next = { ...result.query, sort_by: field, sort_order: 'desc' };
    if (mode === 'manual') setDraft(next);
    else setParsed((prev) => ({ ...prev, query: next }));
    search(next, confirmedText);
  }
  function download(scope) {
    run('export', '/market/export', { query: result.query, scope }, (response) => {
      const url = URL.createObjectURL(new Blob([response.csv], { type: 'text/csv;charset=utf-8;' }));
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = response.filename;
      document.body.appendChild(anchor); anchor.click(); anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  }
  const pending = busy.parse || busy.search;
  const all = result?.matching_summary;
  const top = result?.top_summary;
  const topCount = result?.items.length ?? 0;
  const sectorLabel = result && sectorName(result.query.sector);
  const clusterRows = all && [0, 1, 2].map((id) => ({ name: `Cụm ${id}`, count: all.cluster_counts[id], color: CLUSTER_COLORS[id] }));
  const reportFact = (key) => report?.verified_facts?.[key]?.display ?? '—';
  const reportButton = <button className="button button-primary" disabled={pending || busy.report}
    onClick={() => run('report', '/market/report', { query: result.query, business_request: confirmedText }, setReport)}>
    {report && <Sparkles size={16}/>}{busy.report ? 'Đang tạo báo cáo…' : report ? 'Tạo lại báo cáo thị trường' : 'Tạo báo cáo thị trường'}
  </button>;

  return <div className="page-enter market-explorer">
    <div className="page-intro"><div>
      <h1>Khám phá thị trường</h1><p>Sàng lọc đô thị từ dữ liệu phát thải để xác định phạm vi nghiên cứu thị trường công nghệ xanh.</p>
    </div><span className="year-pill"><Telescope size={16}/> EDGAR 2024 · K=3</span></div>
    <div className="market-mode-switch" role="group" aria-label="Chế độ tìm kiếm">
      {[['ai', 'Tìm kiếm bằng AI'], ['manual', 'Tìm kiếm theo bộ lọc']].map(([key, label]) =>
        <button key={key} type="button" aria-pressed={mode === key} aria-controls="market-search-panel"
          onClick={() => changeMode(key)}>{key === 'ai' ? <Sparkles size={17}/> : <Search size={17}/>} {label}</button>)}
    </div>
    <div id="market-search-panel">
      {mode === 'ai' ? <Panel title={<><Sparkles size={20}/> Tìm kiếm bằng AI</>}>
        <form onSubmit={(e) => { e.preventDefault(); parse(); }}>
          <label htmlFor="market-request" className="input-label">Yêu cầu nghiên cứu</label>
          <textarea id="market-request" rows={4} maxLength={4000} minLength={5} required value={text} disabled={pending}
            onChange={(e) => changeText(e.target.value)} placeholder={EXAMPLE}/>
          <div className="market-actions"><button type="button" className="button button-outline" disabled={pending} onClick={() => changeText(EXAMPLE)}>Dùng yêu cầu mẫu</button>
            <button type="submit" className="button button-primary" disabled={pending || text.trim().length < 5}><Sparkles size={16}/>{busy.parse ? 'Đang phân tích…' : busy.search ? 'Đang truy vấn…' : 'Tìm kiếm bằng AI'}</button></div>
        </form>
        <p className="ce-scope market-search-help">Nếu yêu cầu có điều kiện chưa hỗ trợ, hãy chỉnh sửa trước khi tìm kiếm.</p>
        {busy.parse && <Loading text="Gemini đang chuyển yêu cầu thành bộ lọc…"/>}
        {errors.parse && <ErrorBox message={errors.parse}/>}
        {parsed?.unsupported_criteria.length > 0 && <ErrorBox message={`Chưa thể tìm kiếm. Điều kiện chưa hỗ trợ: ${parsed.unsupported_criteria.map((item) => item.trim().replace(/[.!?]+$/u, '')).join('; ')}. Hãy chỉnh sửa yêu cầu rồi tìm kiếm lại.`}/>}
      </Panel> : <Panel title={<><Search size={20}/> Tìm kiếm theo bộ lọc</>}>
        <form onSubmit={manualSearch}>
          <fieldset disabled={pending} className="market-fields">
            <div className="market-country-field">
              <label htmlFor="market-countries">Quốc gia / vùng lãnh thổ</label>
              <select id="market-countries" multiple size={5} value={draft.countries} onChange={(e) => edit('countries', Array.from(e.target.selectedOptions, (option) => option.value))}>
                {countries.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
              </select>
            </div>
            <label>Lĩnh vực GHG<select id="market-sector" value={draft.sector} onChange={(e) => edit('sector', e.target.value)}><option value="all">Tất cả lĩnh vực</option>{SECTORS.map((s) => <option key={s} value={s}>{SECTOR_LABELS[s]}</option>)}</select></label>
            <label>Tỷ trọng phát thải tối thiểu (%)<input id="market-min" type="number" min="0" max="100" step="any" disabled={draft.sector === 'all'} value={draft.min_sector_share_percent ?? ''} placeholder="Không giới hạn" onChange={(e) => edit('min_sector_share_percent', e.target.value === '' ? null : Number(e.target.value))}/></label>
            <label>Cụm K-Means<select id="market-cluster" value={draft.cluster_id ?? ''} onChange={(e) => edit('cluster_id', e.target.value === '' ? null : Number(e.target.value))}><option value="">Tất cả cụm</option>{[0, 1, 2].map((id) => <option key={id} value={id}>Cụm {id}</option>)}</select></label>
            <label>Sắp xếp (giảm dần)<select id="market-sort" value={draft.sort_by} onChange={(e) => edit('sort_by', e.target.value)}>{Object.entries(SORT_LABELS).map(([key, value]) => <option key={key} value={key} disabled={draft.sector === 'all' && key !== 'total_ghg'}>{value}</option>)}</select></label>
            <label>Số kết quả Top N<select id="market-limit" value={draft.limit} onChange={(e) => edit('limit', Number(e.target.value))}>{[5, 10, 20, 50].map((n) => <option key={n} value={n}>{n}</option>)}</select></label>
          </fieldset>
          {draft.sector === 'all' && <p className="ce-scope">Tất cả lĩnh vực: xếp theo tổng GHG; ngưỡng tỷ trọng và sắp xếp theo lĩnh vực được vô hiệu hóa.</p>}
          <div className="market-actions"><button type="submit" className="button button-primary" disabled={pending}><Search size={16}/>{busy.search ? 'Đang truy vấn…' : 'Tìm kiếm'}</button>
            <button type="button" className="button button-outline" onClick={() => { invalidate(); setDraft({ ...INITIAL_QUERY, countries: [] }); }}>Đặt lại bộ lọc</button></div>
        </form>
      </Panel>}
    </div>
    {errors.search && <ErrorBox message={errors.search}/>}
    {busy.search && <Loading text="Python đang lọc và xếp hạng toàn bộ tập phù hợp…"/>}
    {result && <div className="market-results" aria-live="polite">
      <AppliedConditions query={result.query} context={mode === 'ai' ? parsed : null}/>
      <section className="market-research-scope" aria-labelledby="market-scope-heading">
      <h2 id="market-scope-heading">Phạm vi nghiên cứu</h2>
      <div className="stat-grid">
        <div className="stat-card"><div className="stat-icon green"><Building2 size={23}/></div><span>Toàn bộ đô thị phù hợp</span><strong>{num(all.city_count)}</strong><small>Trong {num(result.source_city_count)} đô thị</small></div>
        <div className="stat-card"><div className="stat-icon blue"><Globe2 size={23}/></div><span>Quốc gia trong tập phù hợp</span><strong>{num(all.country_count)}</strong><small>Tính trên toàn bộ kết quả</small></div>
        <div className="stat-card"><div className="stat-icon orange"><Layers3 size={23}/></div><span>{result.query.sector === 'all' ? 'Phạm vi lĩnh vực' : 'Tỷ trọng trung bình'}</span><strong>{result.query.sector === 'all' ? 'Tất cả' : all.mean_sector_share_percent == null ? '—' : pct(all.mean_sector_share_percent, 2)}</strong><small>{sectorLabel} · toàn bộ tập phù hợp</small></div>
        <div className="stat-card"><div className="stat-icon purple"><Building2 size={23}/></div><span>Top N đang hiển thị</span><strong>{num(topCount)}</strong><small>Giới hạn được chọn: {result.query.limit}</small></div>
      </div>
      {topCount > 0 && <TopSubsetSummary summary={top} count={topCount}/>}
      </section>
      {!all.city_count ? <Panel><Empty>Không có đô thị đáp ứng tiêu chí. Hãy điều chỉnh quốc gia, cụm hoặc ngưỡng tỷ trọng rồi tìm kiếm lại.</Empty></Panel> : <>
        <Panel title="Danh sách đô thị phù hợp" subtitle={`${num(topCount)} đô thị đang hiển thị · ${sectorLabel}`} className="market-results-table"
          action={<div className="market-actions"><button className="button button-outline" disabled={busy.export || pending} onClick={() => download('top')}><Download size={15}/> CSV Top N</button><button className="button button-outline" disabled={busy.export || pending} onClick={() => download('matching')}>CSV toàn bộ ({num(all.city_count)})</button></div>}>
          <div className="ce-table-scroll market-table-scroll" role="region" aria-label="Bảng đô thị phù hợp" tabIndex={0}><table className="ce-table market-table"><thead><tr>
            <th scope="col">Đô thị</th><th scope="col">Quốc gia</th><th scope="col">Cụm</th>
            {[['sector_share', 'Tỷ trọng (%)'], ['sector_emissions', 'GHG lĩnh vực (tấn/năm)'], ['total_ghg', 'Tổng GHG (tấn/năm)']].map(([key, label]) => <th scope="col" key={key} aria-sort={result.query.sort_by === key ? result.query.sort_order === 'asc' ? 'ascending' : 'descending' : 'none'}><button type="button" disabled={pending || (result.query.sector === 'all' && key !== 'total_ghg')} onClick={() => sort(key)}>{label}<ArrowUpDown size={12} aria-hidden="true"/></button></th>)}<th scope="col">Hồ sơ</th>
          </tr></thead><tbody>{result.items.map((city) => <tr key={city.city_id}>
            <th scope="row">{city.city_name}</th><td>{city.country_name}</td>
            <td><span className="market-cluster-dot" style={{ background: CLUSTER_COLORS[city.cluster_id] }}/>{city.cluster_id}</td>
            <td>{city.sector_share_percent == null ? '—' : pct(city.sector_share_percent, 2)}</td>
            <td><CityGhgValue value={city.sector_emissions} sector={sectorLabel} group="market-ghg"/></td>
            <td><CityGhgValue value={city.ghg_total_2024} label="Tổng GHG" group="market-ghg"/></td>
            <td><button className="market-text-button" onClick={() => onSelectCity(city.city_id)}>Mở hồ sơ</button></td>
          </tr>)}</tbody></table></div>
          <p className="ce-scope">Có thể cuộn ngang bảng trên màn hình nhỏ. Nhấn tiêu đề cột số liệu để xếp lại toàn bộ tập phù hợp rồi lấy Top N.</p>
          {errors.export && <ErrorBox message={errors.export}/>}{busy.export && <Loading text="Đang chuẩn bị CSV từ dữ liệu thật…"/>}<Note>Thứ tự chỉ theo tiêu chí phát thải, không phải điểm cơ hội kinh doanh. Dữ liệu phát thải không xác nhận nhu cầu mua công nghệ.</Note>
        </Panel>
        <div className="market-visuals">
          <Panel title="Bản đồ đô thị phù hợp" subtitle="Nhấn một điểm để mở hồ sơ Tra cứu đô thị">
            <WorldMap points={result.map.points} onSelectCity={onSelectCity} fitMatchingPoints/>
            <p className="map-caption">Hiển thị {num(result.map.shown)}/{num(result.map.total_matching)} đô thị phù hợp.</p>
            {result.map.shown === 0 && <Empty>Chưa có tọa độ hợp lệ để hiển thị trên bản đồ.</Empty>}
          </Panel>
          <Panel title="Phân bố theo cụm K-Means" subtitle="Toàn bộ tập phù hợp, không chỉ Top N"><div className="market-cluster-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={clusterRows} margin={{ left: 0, right: 15, top: 8, bottom: 8 }}><CartesianGrid vertical={false} strokeDasharray="3 5"/><XAxis dataKey="name" tick={{ fontSize: 12 }}/><YAxis allowDecimals={false} tick={{ fontSize: 11 }}/><Tooltip formatter={(v) => [num(v), 'Đô thị']}/><Bar dataKey="count" maxBarSize={55} radius={[6, 6, 0, 0]}>{clusterRows.map((row) => <Cell key={row.name} fill={row.color}/>)}</Bar></BarChart></ResponsiveContainer></div><div className="market-cluster-counts">{clusterRows.map((row) => <span key={row.name}>{row.name}: <strong>{num(row.count)}</strong></span>)}</div></Panel>
        </div>
        <RankingChart query={result.query} items={result.items}/>
        <Panel title={<><Sparkles size={20}/> Báo cáo nghiên cứu thị trường bằng Gemini</>} className="market-report-panel">
          {report ? <div className="ce-ai-action"><p>Báo cáo gắn với bộ lọc đã xác nhận và phân biệt toàn bộ tập phù hợp với Top N.</p>{reportButton}</div>
            : <div className="market-report-empty">
              <FileText size={26} aria-hidden="true"/>
              {(!busy.report || errors.report) && <p>Chưa có báo cáo cho phạm vi nghiên cứu hiện tại.</p>}
              {reportButton}
            </div>}
          {busy.report && <Loading text="Gemini đang tổng hợp dữ liệu nghiên cứu…"/>}{errors.report && <ErrorBox message={errors.report}/>}
          <div aria-live="polite">{report ? <article className="ce-report">
            {report.verified_facts && <div className="ce-table-scroll" role="region" aria-label="Thống kê toàn bộ tập phù hợp và Top N" tabIndex={0}>
              <table className="ce-table market-report-facts">
                <thead><tr><th scope="col">Phạm vi</th><th scope="col">Đô thị</th><th scope="col">Quốc gia</th><th scope="col">Tỷ trọng TB</th>{[0, 1, 2].map((id) => <th key={id} scope="col">Cụm {id}</th>)}</tr></thead>
                <tbody>{[['matching', 'Toàn bộ tập phù hợp'], ['top', 'Top N hiển thị']].map(([scope, label]) => <tr key={scope}>
                  <th scope="row">{label}</th>
                  <td>{reportFact(`${scope}.city_count`)}</td>
                  <td>{reportFact(`${scope}.country_count`)}</td>
                  <td>{reportFact(`${scope}.mean_sector_share_percent`)}</td>
                  {[0, 1, 2].map((id) => <td key={id}>{reportFact(`${scope}.clusters.${id}.city_count`)} ({reportFact(`${scope}.clusters.${id}.city_percentage`)})</td>)}
                </tr>)}</tbody>
              </table>
            </div>}
            <h3>Yêu cầu và phạm vi nghiên cứu</h3><p>{report.report.research_request}</p><h3>Đặc điểm phát thải</h3><p>{report.report.emissions_profile}</p><h3>Phân bố theo cụm</h3><p>{report.report.cluster_distribution}</p>
            <h3>Một số đô thị trong Top N</h3>{report.report.city_comparisons.map((city, i) => { const source = report.representative_cities.find((c) => c.city_id === city.city_id); return <div key={i}><strong>{source?.city_name} · {source?.country_name}</strong>{report.verified_facts && <p className="ce-scope">Thứ hạng {reportFact(`cities.${city.city_id}.rank`)} · Cụm {reportFact(`cities.${city.city_id}.cluster_id`)} · Tỷ trọng {reportFact(`cities.${city.city_id}.sector_share_percent`)} · Chênh lệch với trung bình toàn bộ tập phù hợp: {reportFact(`cities.${city.city_id}.share_gap_matching_pp`)}</p>}<p>{city.text}</p></div>; })}
            <h3>Liên hệ công nghệ sơ bộ</h3><p>{report.report.preliminary_technology_link}</p><h3>Thông tin cần bổ sung</h3><ul>{report.report.additional_information.map((v, i) => <li key={i}>{v}</li>)}</ul><h3>Giới hạn kết luận</h3><p>{report.report.limitations}</p>
          </article> : null}</div>
        </Panel>
      </>}
    </div>}
  </div>;
}
