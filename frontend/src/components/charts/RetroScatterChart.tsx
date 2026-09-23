import React, { useState } from 'react';
import { CHART_DIMENSIONS, RETRO_COLORS, buildLinearDomainScale, chartInnerHeight } from './scales';

interface ScatterPoint {
  x: number;
  y: number;
  label?: string;
}

interface RetroScatterChartProps {
  points: ScatterPoint[];
  color?: string;
  xUnit?: string;
  yUnit?: string;
}

export const RetroScatterChart: React.FC<RetroScatterChartProps> = ({ points, color, xUnit, yUnit }) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const { svgWidth, svgHeight, paddingLeft, paddingRight, paddingTop } = CHART_DIMENSIONS;

  const xValues = points.map((p) => p.x);
  const yValues = points.map((p) => p.y);
  const xScale = buildLinearDomainScale(xValues, [paddingLeft, svgWidth - paddingRight]);
  const yScale = buildLinearDomainScale(yValues, [paddingTop + chartInnerHeight, paddingTop]);
  const dotColor = color || RETRO_COLORS[0];

  return (
    <div className="relative w-full overflow-hidden select-none pt-2">
      <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-48 sm:h-56 overflow-visible">
        {/* Grid lines at quartile intervals */}
        {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
          const y = paddingTop + chartInnerHeight * (1 - frac);
          return (
            <line
              key={frac}
              x1={paddingLeft}
              y1={y}
              x2={svgWidth - paddingRight}
              y2={y}
              stroke="#CBD5E1"
              strokeWidth="1"
              strokeDasharray="3 3"
            />
          );
        })}

        <line
          x1={paddingLeft}
          y1={paddingTop + chartInnerHeight}
          x2={svgWidth - paddingRight}
          y2={paddingTop + chartInnerHeight}
          stroke="#000"
          strokeWidth="2"
        />
        <line
          x1={paddingLeft}
          y1={paddingTop}
          x2={paddingLeft}
          y2={paddingTop + chartInnerHeight}
          stroke="#000"
          strokeWidth="2"
        />

        {points.map((pt, idx) => (
          <g
            key={idx}
            className="cursor-pointer"
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
          >
            <circle
              cx={xScale(pt.x)}
              cy={yScale(pt.y)}
              r={5}
              fill={dotColor}
              stroke="#000"
              strokeWidth="2"
              className="transition-transform hover:scale-125"
            />
          </g>
        ))}
      </svg>

      {hoveredIdx !== null && (
        <div
          className="absolute z-20 pointer-events-none transform -translate-x-1/2 -translate-y-full -mt-2.5 bg-black text-white px-2 py-1 border-2 border-[#FFD200] font-arcade-mono text-[10px] font-bold tracking-wider retro-shadow-sm whitespace-nowrap"
          style={{
            left: `${(xScale(points[hoveredIdx].x) / svgWidth) * 100}%`,
            top: `${(yScale(points[hoveredIdx].y) / svgHeight) * 100}%`,
          }}
        >
          {points[hoveredIdx].label && <div className="text-[#FFD200]">{points[hoveredIdx].label}</div>}
          <div>
            {points[hoveredIdx].x} {xUnit || ''} / {points[hoveredIdx].y} {yUnit || ''}
          </div>
        </div>
      )}
    </div>
  );
};
