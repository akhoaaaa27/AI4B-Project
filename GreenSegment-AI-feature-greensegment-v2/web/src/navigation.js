const PAGES = new Set(['home', 'overview', 'city', 'market', 'about', 'advisor']);

// Hash URLs work on the existing Vite/static host without server rewrite rules.
export function readRoute() {
  const [path, query = ''] = window.location.hash.replace(/^#\/?/, '').split('?');
  const page = path || 'home';
  return {
    page: PAGES.has(page) ? page : 'home',
    cityId: ['city', 'advisor'].includes(page) ? new URLSearchParams(query).get('city') || null : null,
  };
}

export function pageHref(page, cityId) {
  const path = page === 'home' ? '' : page;
  const query = cityId && ['city', 'advisor'].includes(page) ? `?city=${encodeURIComponent(cityId)}` : '';
  return `#/${path}${query}`;
}

export function navigate(page, cityId) {
  window.location.hash = pageHref(page, cityId);
}
