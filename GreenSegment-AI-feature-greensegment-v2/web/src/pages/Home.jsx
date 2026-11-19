import React from 'react';
import { ArrowRight, BarChart3, MapPin, Telescope } from 'lucide-react';
import { pageHref } from '../navigation.js';

const FEATURES = [
  { page: 'overview', Icon: BarChart3, title: 'Tổng quan',
    description: 'Khám phá cơ cấu phát thải khí nhà kính, phân bố địa lý và các cụm đô thị.' },
  { page: 'city', Icon: MapPin, title: 'Tra cứu đô thị',
    description: 'Tra cứu từng đô thị, đọc hồ sơ phát thải và so sánh với đặc trưng cụm.' },
  { page: 'market', Icon: Telescope, title: 'Khám phá thị trường',
    description: 'Khám phá các góc nhìn thị trường công nghệ xanh từ đặc điểm phát thải đô thị.' },
];

export default function Home({ selectedCityId }) {
  return <div className="home-page page-enter">
    <section className="home-hero" aria-labelledby="home-title">
      <h1 id="home-title"><span>GreenSegment</span> Artificial Intelligence</h1>
      <p className="home-description">Nền tảng phân tích cơ cấu phát thải khí nhà kính của các đô thị, hỗ trợ khám phá dữ liệu khoa học, so sánh các nhóm đô thị và tìm hiểu thị trường công nghệ xanh.</p>
      <a className="home-cta" href={pageHref('overview')}>Khám phá dữ liệu <ArrowRight size={20} aria-hidden="true"/></a>
    </section>
    <section className="home-features" aria-label="Khám phá các tính năng">
      {FEATURES.map(({ page, Icon, title, description }) => <a key={page} className="home-feature-card"
        href={pageHref(page, selectedCityId)} aria-labelledby={`feature-${page}`}>
        <Icon className="home-feature-icon" size={30} strokeWidth={1.7} aria-hidden="true"/>
        <h2 id={`feature-${page}`}>{title}</h2>
        <p>{description}</p>
        <span className="home-feature-arrow"><ArrowRight size={18} aria-hidden="true"/></span>
      </a>)}
    </section>
  </div>;
}
