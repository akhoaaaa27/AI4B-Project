import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowUpRight, Leaf, Pause, Play, Sparkles, Users, ScanLine, Sprout } from 'lucide-react';
import './preview.css';

function useReducedMotion() {
  const [reduced, setReduced] = useState(() => matchMedia('(prefers-reduced-motion: reduce)').matches);
  useEffect(() => {
    const query = matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(query.matches);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  return reduced;
}

function EarthScene({ paused, reduced, particles, onMode }) {
  const host = useRef(null);
  const controller = useRef(null);
  const preferences = useRef({ paused, reduced, particles });
  const [mode, setMode] = useState('loading');
  preferences.current = { paused, reduced, particles };
  useEffect(() => {
    let cancelled = false;
    import('./scene.js').then(({ createLivingEarthScene }) => {
      if (cancelled) return;
      controller.current = createLivingEarthScene(host.current, {
        ...preferences.current,
        onMode: (next) => { if (!cancelled) { setMode(next); onMode(next); } },
      });
    }).catch(() => { if (!cancelled) { setMode('fallback'); onMode('fallback'); } });
    return () => { cancelled = true; controller.current?.dispose(); controller.current = null; };
  }, [onMode]);
  useEffect(() => controller.current?.setPreferences(preferences.current), [paused, reduced, particles]);
  return <div className="le-visual" role="img" aria-label="Trái Đất ba chiều lơ lửng trên lòng bàn tay điêu khắc graphite, trong ánh sáng xanh dịu.">
    <div ref={host} className={`le-webgl ${mode === 'fallback' ? 'le-webgl-hidden' : ''}`} aria-hidden="true"/>
    {mode !== 'ready' && <img className="le-poster" src="/living-earth/scene-poster.webp" alt="" aria-hidden="true"/>}
    <p className="le-scene-status" role="status">{mode === 'loading' ? 'Đang chuẩn bị cảnh…' : mode === 'fallback' ? 'Ảnh tĩnh · Chế độ 3D hiện không khả dụng' : reduced ? 'Cảnh tĩnh · Theo thiết lập giảm chuyển động' : paused ? 'Chuyển động đã tạm dừng' : 'Một vòng quay · 60 giây'}</p>
  </div>;
}

const audiences = [
  { Icon: Users, index: '01', title: 'Hiểu nơi mình sống', text: 'Một góc nhìn về cơ cấu phát thải của các đô thị.' },
  { Icon: ScanLine, index: '02', title: 'Khơi mở nghiên cứu', text: 'Từ dữ liệu đến những câu hỏi đáng tìm hiểu hơn.' },
  { Icon: Sprout, index: '03', title: 'Nuôi dưỡng ý tưởng xanh', text: 'Thêm ngữ cảnh cho hành trình nghiên cứu thị trường.' },
];

function LivingEarthPreview() {
  const reduced = useReducedMotion();
  const [paused, setPaused] = useState(false);
  const [particles, setParticles] = useState(true);
  const [mode, setMode] = useState('loading');
  return <main className="le-page">
    <div className="le-forest-light" aria-hidden="true"/>
    <header className="le-header">
      <a className="le-brand" href="/" aria-label="GreenSegment AI — về giao diện hiện tại"><span><Leaf size={23}/></span>GreenSegment <b>AI</b></a>
      <span className="le-prototype-badge"><i aria-hidden="true"/>Visual prototype <span>— 01</span></span>
    </header>
    <section className="le-hero" aria-labelledby="le-title">
      <div className="le-intro">
        <p className="le-eyebrow"><span/>LIVING EARTH</p>
        <h1 id="le-title">Hành tinh<br/>trong tay<br/>{' '}<em>chúng ta.</em></h1>
        <p className="le-hero-caption">Bức tranh phát thải đô thị toàn cầu</p>
        <p className="le-description">Khám phá đặc điểm cơ cấu phát thải khí nhà kính của các đô thị trên thế giới.</p>
        <div className="le-actions">
          <a className="le-back-link" href="/">Về giao diện hiện tại <ArrowUpRight size={17}/></a>
          <a className="le-study-link" href="#le-study">Xem ý tưởng</a>
        </div>
        <p className="le-study-note"><span/>THE PLANET IN OUR HANDS</p>
      </div>
      <div className="le-stage">
        <div className="le-stage-glow" aria-hidden="true"/>
        <EarthScene paused={paused} reduced={reduced} particles={particles} onMode={setMode}/>
        <div className="le-scene-controls" aria-label="Điều khiển cảnh thử nghiệm">
          <button type="button" onClick={() => setPaused((value) => !value)} aria-pressed={paused || reduced}
            disabled={reduced || mode !== 'ready'}>{paused || reduced ? <Play size={14}/> : <Pause size={14}/>}{mode === 'fallback' ? 'Ảnh tĩnh' : reduced ? 'Cảnh tĩnh' : paused ? 'Tiếp tục' : 'Tạm dừng'}</button>
          <button type="button" aria-pressed={particles} onClick={() => setParticles((value) => !value)} disabled={mode !== 'ready'}><Sparkles size={14}/>Hạt sáng</button>
        </div>
      </div>
    </section>
    <section className="le-study" id="le-study" aria-label="Nội dung minh họa để đánh giá tương phản">
      <div className="le-study-heading"><span>THIÊN NHIÊN. KHOA HỌC. CON NGƯỜI.</span><p>Một hành tinh. Nhiều góc nhìn.</p></div>
      <div className="le-sample-cards">{audiences.map(({ Icon, index, title, text }) => <article key={index}>
        <div className="le-card-top"><Icon size={21}/><span>{index}</span></div><h2>{title}</h2><p>{text}</p>
      </article>)}</div>
    </section>
    <footer className="le-footer">
      <p>GreenSegment AI <span>·</span> Living Earth visual study</p>
      <details><summary>Tài nguyên & ghi chú</summary><div>
        <p>Đây là bản thử nghiệm hình ảnh độc lập. Các thẻ bên trên là nội dung minh họa, không phải kết quả phân tích.</p>
        <p>Texture Trái Đất: <a href="https://www.solarsystemscope.com/textures/" target="_blank" rel="noreferrer">Solar System Scope</a>, CC BY 4.0, dựa trên dữ liệu NASA. Không thể hiện số liệu phát thải hoặc thời tiết hiện tại.</p>
        <p>Bàn tay: <a href="https://github.com/immersive-web/webxr-input-profiles/tree/main/packages/assets/profiles/generic-fixed-hand" target="_blank" rel="noreferrer">Immersive Web / generic-fixed-hand</a>, MIT. Mô hình nhẹ được phủ vật liệu graphite cho prototype; chưa phải bản điêu khắc điện ảnh độ phân giải cao.</p>
        <p>Chuyển động tự dừng khi cảnh khuất, tab ẩn hoặc hệ thống yêu cầu giảm chuyển động. Mobile dùng giới hạn đồ họa thấp hơn.</p>
      </div></details>
    </footer>
  </main>;
}

createRoot(document.getElementById('living-earth-root')).render(<LivingEarthPreview/>);
