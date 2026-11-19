import React from 'react';
import { compactGhg, fullGhg } from '../ghgFormatting.js';
import CityValueTooltip from './CityValueTooltip.jsx';

export default function CityGhgValue({ value, sector, label = `GHG ${sector}`, group }) {
  const fullValue = fullGhg(value);
  if (fullValue == null) return <span aria-label="Không có dữ liệu GHG">—</span>;

  return <CityValueTooltip className="city-ghg-value" label={`${label}: ${fullValue}`} description={fullValue} group={group} dismissOnBlur>
    {compactGhg(value)}
  </CityValueTooltip>;
}
