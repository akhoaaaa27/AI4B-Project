import React, { useEffect, useState } from 'react';
import { Menu } from 'lucide-react';
import { apiGet } from './api.js';
import Sidebar from './components/Sidebar.jsx';
import Overview from './pages/Overview.jsx';
import CityExplorer from './pages/CityExplorer.jsx';
import GreenAdvisor from './pages/GreenAdvisor.jsx';
import About from './pages/About.jsx';
import MarketExplorer from './pages/MarketExplorer.jsx';

const INITIAL_FILTERS = { country: '', cluster_id: '', sector: '' };

export default function App() {
  const [page, setPage] = useState('overview');
  // Map scope and the last detailed profile travel together, including across page navigation.
  const [overview, setOverview] = useState({ filters: INITIAL_FILTERS, analysisClusterId: 0, mapResetVersion: 0 });
  const [countries, setCountries] = useState([]);
  const [selectedCityId, setSelectedCityId] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);

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
  const onSelectCityFromMap = (cityId) => { setSelectedCityId(String(cityId)); setPage('city'); window.scrollTo({ top: 0, behavior: 'smooth' }); };

  return <div className="app-shell">
    <Sidebar page={page} onPage={setPage} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen}/>
    <div className="main-shell">
      <div className="mobile-topbar"><button aria-label="Mở điều hướng" onClick={() => setMobileOpen(true)}><Menu size={22}/></button>
        <strong>GreenSegment AI</strong><span>2024</span></div>
      <div className="main-inner">
        {page === 'overview' && <Overview filters={overview.filters} analysisClusterId={overview.analysisClusterId}
          mapResetVersion={overview.mapResetVersion} onFilter={onFilter} countries={countries} onSelectCity={onSelectCityFromMap}/>}
        {page === 'market' && <MarketExplorer countries={countries} onSelectCity={onSelectCityFromMap}/>}
        {page === 'city' && <CityExplorer selectedCityId={selectedCityId}
          onSelectCity={(id) => setSelectedCityId(String(id))} onGoAdvisor={() => { setPage('advisor'); window.scrollTo(0, 0); }}/>} 
        {page === 'advisor' && <GreenAdvisor selectedCityId={selectedCityId} onSelectCity={(id) => setSelectedCityId(String(id))}/>}
        {page === 'about' && <About/>}
      </div>
    </div>
  </div>;
}
