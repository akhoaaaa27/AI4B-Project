import React, { useEffect, useRef, useState } from 'react';
import { Menu, X } from 'lucide-react';
import gsaiLogo from '../assets/gsai-logo-transparent.png';
import { pageHref } from '../navigation.js';

const DESTINATIONS = [
  ['home', 'Trang chủ'],
  ['overview', 'Tổng quan'],
  ['city', 'Tra cứu đô thị'],
  ['market', 'Khám phá thị trường'],
  ['about', 'Giới thiệu'],
];

export default function GlobalHeader({ page, selectedCityId }) {
  const [open, setOpen] = useState(false);
  const headerRef = useRef(null);
  const navRef = useRef(null);
  const toggleRef = useRef(null);

  useEffect(() => { setOpen(false); }, [page]);

  useEffect(() => {
    if (!open) return;
    const frame = requestAnimationFrame(() => {
      navRef.current?.querySelector('[aria-current="page"]')?.focus();
    });
    const outside = (event) => {
      if (!headerRef.current?.contains(event.target)) setOpen(false);
    };
    const wide = window.matchMedia('(min-width: 901px)');
    const resize = () => { if (wide.matches) setOpen(false); };
    document.addEventListener('pointerdown', outside);
    wide.addEventListener('change', resize);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener('pointerdown', outside);
      wide.removeEventListener('change', resize);
    };
  }, [open]);

  return <header className={`global-header${open ? ' menu-open' : ''}`} ref={headerRef}
    onKeyDown={(event) => {
      if (event.key === 'Escape' && open) {
        setOpen(false); toggleRef.current?.focus();
      }
    }} onBlur={(event) => {
      if (open && !event.currentTarget.contains(event.relatedTarget)) setOpen(false);
    }}>
    <a className="skip-link" href="#main-content" onClick={(event) => {
      event.preventDefault(); document.getElementById('main-content')?.focus();
    }}>Đến nội dung chính</a>
    <div className="global-header-inner">
      <a className="brand global-brand" href={pageHref('home')} aria-label="GSAI — Trang chủ"
        onClick={() => { setOpen(false); if (page === 'home') window.scrollTo({ top: 0, behavior: 'instant' }); }}>
        <img className="global-brand-logo" src={gsaiLogo} width={44} height={44} alt=""/>
        <strong>GSAI</strong>
      </a>
      <button className="navigation-toggle" ref={toggleRef} type="button" aria-controls="primary-navigation"
        aria-expanded={open} aria-label={open ? 'Đóng điều hướng' : 'Mở điều hướng'} onClick={() => setOpen(!open)}>
        {open ? <X size={22} aria-hidden="true"/> : <Menu size={22} aria-hidden="true"/>}
      </button>
      <nav id="primary-navigation" className="floating-navigation" aria-label="Điều hướng chính" ref={navRef}>
        {DESTINATIONS.map(([id, label]) => <a key={id} href={pageHref(id, selectedCityId)}
          className={`navigation-link${page === id ? ' active' : ''}`} aria-current={page === id ? 'page' : undefined}
          onClick={() => { setOpen(false); if (page === id) window.scrollTo({ top: 0, behavior: 'instant' }); }}>{label}</a>)}
      </nav>
      <span className="header-balance" aria-hidden="true"/>
    </div>
  </header>;
}
