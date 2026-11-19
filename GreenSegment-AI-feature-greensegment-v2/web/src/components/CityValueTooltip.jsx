import React, { useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

export default function CityValueTooltip({ children, label, description, className, dismissOnBlur = false, group }) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const pinned = useRef(false);
  const buttonRef = useRef(null);
  const tooltipRef = useRef(null);
  const tooltipId = useId();
  const close = () => { pinned.current = false; setOpen(false); };
  const show = () => {
    if (group) document.dispatchEvent(new CustomEvent('value-tooltip-open', { detail: { group, tooltipId } }));
    setOpen(true);
  };

  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const button = buttonRef.current;
      const tooltip = tooltipRef.current;
      if (!button || !tooltip) return;
      const anchor = button.getBoundingClientRect();
      const width = tooltip.offsetWidth, height = tooltip.offsetHeight;
      const left = Math.max(12, Math.min(anchor.left + anchor.width / 2 - width / 2, window.innerWidth - width - 12));
      const below = anchor.bottom + 8;
      const top = Math.max(12, Math.min(below + height <= window.innerHeight - 12 ? below : anchor.top - height - 8, window.innerHeight - height - 12));
      setPosition((old) => old.top === top && old.left === left ? old : { top, left });
    };
    const outside = (event) => {
      if (!buttonRef.current?.contains(event.target) && !tooltipRef.current?.contains(event.target)) close();
    };
    const escape = (event) => { if (event.key === 'Escape') close(); };
    const anotherTooltip = ({ detail }) => {
      if (detail?.group === group && detail.tooltipId !== tooltipId) close();
    };
    place();
    const observer = new ResizeObserver(place);
    observer.observe(tooltipRef.current);
    window.addEventListener('resize', place);
    window.addEventListener('scroll', place, true);
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape);
    if (group) document.addEventListener('value-tooltip-open', anotherTooltip);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', place);
      window.removeEventListener('scroll', place, true);
      document.removeEventListener('pointerdown', outside);
      document.removeEventListener('keydown', escape);
      if (group) document.removeEventListener('value-tooltip-open', anotherTooltip);
    };
  }, [open, group, tooltipId]);

  return <>
    <button type="button" className={className} ref={buttonRef}
      aria-label={label} aria-expanded={open} aria-describedby={open ? tooltipId : undefined}
      onMouseEnter={show}
      onMouseLeave={() => { if (!pinned.current && document.activeElement !== buttonRef.current) setOpen(false); }}
      onFocus={show} onBlur={() => { if (dismissOnBlur || !pinned.current) close(); }}
      onClick={() => { if (pinned.current) close(); else { pinned.current = true; show(); } }}>
      {children}
    </button>
    {open && createPortal(<div className="city-value-tooltip" id={tooltipId} role="tooltip" ref={tooltipRef} style={position}>
      {description}
    </div>, document.body)}
  </>;
}
