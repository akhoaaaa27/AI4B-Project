import React from 'react';
import { Info } from 'lucide-react';
import CityValueTooltip from './CityValueTooltip.jsx';

export default function CentroidDistanceHelp() {
  return <CityValueTooltip className="city-distance-help" label="Giải thích khoảng cách đến tâm cụm"
    description="Khoảng cách Euclid giữa cơ cấu tỷ trọng phát thải của đô thị và tâm cụm K-Means trong không gian 7 lĩnh vực. Đây không phải khoảng cách địa lý.">
    <Info size={14} aria-hidden="true"/>
  </CityValueTooltip>;
}
