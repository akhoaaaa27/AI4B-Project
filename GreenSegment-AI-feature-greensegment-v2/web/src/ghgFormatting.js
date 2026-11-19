const unscaledNumber = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 2 });
const scaledNumber = new Intl.NumberFormat('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fullNumber = new Intl.NumberFormat('vi-VN', { maximumSignificantDigits: 21 });

const validGhg = (value) => Number.isFinite(value) && value >= 0;

export function compactGhg(value) {
  if (!validGhg(value)) return '—';
  if (value >= 1_000_000) return `${scaledNumber.format(value / 1_000_000)} triệu`;
  // Keep the original magnitude tier when rounding would jump to the next one.
  if (value >= 1_000) return `${scaledNumber.format(Math.min(value / 1_000, 999.99))} nghìn`;
  if (value > 0 && value < 0.005) return '<0,01';
  return unscaledNumber.format(Math.min(value, 999.99));
}

export function fullGhg(value) {
  return validGhg(value) ? `${fullNumber.format(value)} tấn/năm` : null;
}
