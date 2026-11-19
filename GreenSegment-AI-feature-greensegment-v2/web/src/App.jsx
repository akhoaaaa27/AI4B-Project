import React, { useEffect, useRef, useState } from 'react';
import { apiGet } from './api.js';
import GlobalHeader from './components/GlobalHeader.jsx';
import Home from './pages/Home.jsx';
import { navigate, readRoute } from './navigation.js';
import Overview from './pages/Overview.jsx';
import CityExplorer from './pages/CityExplorer.jsx';
import GreenAdvisor from './pages/GreenAdvisor.jsx';
import About from './pages/About.jsx';
import MarketExplorer from './pages/MarketExplorer.jsx';
import VideoBackground from './components/VideoBackground.jsx';

const INITIAL_FILTERS = { country: '', cluster_id: '', sector: '' };

export default function App() {
  const [route, setRoute] = useState(readRoute);
  const page = route.page;
  const previousPage = useRef(page);
  // Map scope and the last detailed profile travel together, including across page navigation.
  const [overview, setOverview] = useState({ filters: INITIAL_FILTERS, analysisClusterId: 0, mapResetVersion: 0 });
  const [countries, setCountries] = useState([]);
  const [lastCityId, setLastCityId] = useState(route.cityId);
  const selectedCityId = route.cityId ?? lastCityId;

  useEffect(() => {
    const update = () => setRoute(readRoute());
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);

  useEffect(() => { if (route.cityId) setLastCityId(route.cityId); }, [route.cityId]);

  useEffect(() => {
    const titles = { home: 'Trang chủ', overview: 'Tổng quan', city: 'Tra cứu đô thị', market: 'Khám phá thị trường', about: 'Giới thiệu', advisor: 'Gemini Advisor' };
    document.title = `${titles[page]} | GreenSegment AI`;
    if (previousPage.current !== page) {
      window.scrollTo({ top: 0, behavior: 'instant' });
      const heading = document.querySelector('#main-content h1');
      if (heading) { heading.tabIndex = -1; heading.focus({ preventScroll: true }); }
    }
    previousPage.current = page;
  }, [page]);

  useEffect(() => {
    apiGet('/countries').then(setCountries).catch(() => {});
  }, []);

  const onFilter = (key, value) => setOverview((prev) => {
    if (key === 'reset') return { ...prev, filters: INITIAL_FILTERS, mapResetVersion: prev.mapResetVersion + 1 };
    return {
      ...prev,
      filters: { ...prev.filters, [key]: value },
      analysisClusterId: key === 'cluster_id' && value !== '' ? Number(value) : prev.analysisClusterId,
    };
  });
  const onSelectCityFromMap = (cityId) => navigate('city', String(cityId));

  return <div className="app-shell">
    <VideoBackground/>
    <GlobalHeader page={page} selectedCityId={selectedCityId}/>
    <div className="main-shell">
      <main id="main-content" className={`main-inner${page === 'home' ? ' home-container' : ''}`} tabIndex={-1}>
        {page === 'home' && <Home selectedCityId={selectedCityId}/>}
        {page === 'overview' && <Overview filters={overview.filters} analysisClusterId={overview.analysisClusterId}
          mapResetVersion={overview.mapResetVersion} onFilter={onFilter} countries={countries} onSelectCity={onSelectCityFromMap}/>}
        {page === 'market' && <MarketExplorer countries={countries} onSelectCity={onSelectCityFromMap}/>}
        {page === 'city' && <CityExplorer selectedCityId={selectedCityId}
          onSelectCity={(id) => navigate('city', String(id))} onGoAdvisor={() => navigate('advisor', selectedCityId)}/>}
        {page === 'advisor' && <GreenAdvisor selectedCityId={selectedCityId} onSelectCity={(id) => navigate('advisor', String(id))}/>}
        {page === 'about' && <About/>}
      </main>
    </div>
  </div>;
}
