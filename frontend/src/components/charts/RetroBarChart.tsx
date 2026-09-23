import React, { useState } from 'react';
import {
  CHART_DIMENSIONS,
  RETRO_COLORS,
  buildBandScale,
  buildYScale,
  buildYTicks,
  chartInnerHeight,
  niceMax,
} from './scales';

interface RetroBarChartProps {
  labels: string[];
  values: number[];
  color?: string;
  unit?: string;
}

export const RetroBarChart: React.FC<RetroBarChartProps> = ({ labels, values, color, unit }) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const { svgWidth, svgHeight, paddingLeft, paddingRight, paddingTop } = CHART_DIMENSIONS;

  const maxVal = niceMax(Math.max(...values, 0));
  const ticks = buildYTicks(maxVal);
  const xScale = buildBandScale(labels);
  const yScale = buildYScale(maxVal);
  const barColor = color || RETRO_COLORS[0];
  const bandwidth = xScale.bandwidth();

  return (
    <div className="relative w-full overflow-hidden select-none pt-2">
      <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-48 sm:h-56 overflow-visible">
        {ticks.map((t, idx) => {
          const y = yScale(t);
          return (
            <g key={idx}>
              <line
                x1={paddingLeft}
                y1={y}
                x2={svgWidth - paddingRight}
                y2={y}
                stroke="#CBD5E1"
                strokeWidth="1"
                strokeDasharray="3 3"
              />
              <text
                x={paddingLeft - 6}
                y={y + 3.5}
                textAnchor="end"
                className="font-arcade-mono text-[9px] fill-slate-500 font-bold"
              >
                {t}
              </text>
            </g>
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

        {labels.map((lbl, idx) => {
          const val = values[idx] ?? 0;
          const x = xScale(lbl) ?? 0;
          const y = yScale(val);
          const height = paddingTop + chartInnerHeight - y;
          return (
            <g
              key={idx}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              className="cursor-pointer"
            >
              <rect
                x={x}
                y={y}
                width={bandwidth}
                height={Math.max(height, 1)}
                fill={barColor}
                stroke="#000"
                strokeWidth="2"
                className="transition-all duration-300 hover:brightness-110"
              />
              <text
                x={x + bandwidth / 2}
                y={paddingTop + chartInnerHeight + 16}
                textAnchor="middle"
                className="font-arcade-mono text-[9px] sm:text-[10px] fill-black font-bold uppercase"
              >
                {lbl}
              </text>
            </g>
          );
        })}
      </svg>

      {hoveredIdx !== null && (
        <div
          className="absolute z-20 pointer-events-none transform -translate-x-1/2 -translate-y-full -mt-2.5 bg-black text-white px-2 py-1 border-2 border-[#FFD200] font-arcade-mono text-[10px] font-bold tracking-wider retro-shadow-sm whitespace-nowrap"
          style={{
            left: `${(((xScale(labels[hoveredIdx]) ?? 0) + bandwidth / 2) / svgWidth) * 100}%`,
            top: `${(yScale(values[hoveredIdx] ?? 0) / svgHeight) * 100}%`,
          }}
        >
          <div className="text-[#FFD200]">{labels[hoveredIdx]}</div>
          <div>
            {values[hoveredIdx]} {unit || ''}
          </div>
        </div>
      )}
    </div>
  );
};
