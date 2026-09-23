import React, { useState } from 'react';
import { line as d3line } from 'd3-shape';
import {
  CHART_DIMENSIONS,
  RETRO_COLORS,
  buildXPointScale,
  buildYScale,
  buildYTicks,
  chartInnerWidth,
  chartInnerHeight,
  chartLabelStride,
  formatChartValue,
  niceMax,
} from './scales';

interface LineChartProps {
  labels: string[];
  values: number[];
  color?: string;
  unit?: string;
  xLabel?: string;
  yLabel?: string;
}

export const LineChart: React.FC<LineChartProps> = ({ labels, values, color, unit, xLabel, yLabel }) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const { svgWidth, svgHeight, paddingLeft, paddingRight, paddingTop } = CHART_DIMENSIONS;

  const maxVal = niceMax(Math.max(...values, 0));
  const ticks = buildYTicks(maxVal);
  const xScale = buildXPointScale(labels);
  const yScale = buildYScale(maxVal);
  const strokeColor = color || RETRO_COLORS[0];

  const points = values.map((val, idx) => ({ x: xScale(idx), y: yScale(val), val, label: labels[idx] }));

  const lineGenerator = d3line<{ x: number; y: number }>()
    .x((d) => d.x)
    .y((d) => d.y);
  const pathD = lineGenerator(points) || '';
  const areaD = `${pathD} L ${points[points.length - 1]?.x ?? 0},${paddingTop + chartInnerHeight} L ${
    points[0]?.x ?? 0
  },${paddingTop + chartInnerHeight} Z`;

  return (
    <div className="relative w-full overflow-x-auto select-none pt-2">
      <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full min-w-[560px] h-auto overflow-visible" role="group" aria-label={`${yLabel || 'Value'} over ${xLabel || 'category'}`}>
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
                {formatChartValue(t)}
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

        <path d={areaD} fill={strokeColor} fillOpacity={0.12} />
        <path
          d={pathD}
          fill="none"
          stroke="#000000"
          strokeWidth="4"
          strokeLinecap="square"
          strokeLinejoin="miter"
          transform="translate(1.5, 1.5)"
          opacity="0.3"
        />
        <path d={pathD} fill="none" stroke={strokeColor} strokeWidth="2.5" strokeLinecap="square" strokeLinejoin="miter" />

        {points.map((pt, idx) => (
          <g
            key={idx}
            className="cursor-pointer"
            tabIndex={0}
            role="img"
            aria-label={`${pt.label}: ${pt.val} ${unit || ''}`}
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
            onFocus={() => setHoveredIdx(idx)}
            onBlur={() => setHoveredIdx(null)}
          >
            <rect
              x={pt.x - 5}
              y={pt.y - 5}
              width="10"
              height="10"
              fill={strokeColor}
              stroke="#000000"
              strokeWidth="2"
              className="transition-transform hover:scale-125"
            />
          </g>
        ))}

        {labels.map((lbl, idx) => (idx % chartLabelStride(labels.length) === 0 || idx === labels.length - 1) && (
          <text
            key={idx}
            x={xScale(idx)}
            y={paddingTop + chartInnerHeight + 15}
            transform={`rotate(-42 ${xScale(idx)} ${paddingTop + chartInnerHeight + 15})`}
            textAnchor="end"
            className="font-arcade-mono text-[9px] fill-black font-bold"
          >
            {lbl.length > 24 ? `${lbl.slice(0, 23)}…` : lbl}
          </text>
        ))}
        <text x={paddingLeft + chartInnerWidth / 2} y={svgHeight - 7} textAnchor="middle" className="font-arcade-mono text-[10px] fill-slate-600 font-bold">{xLabel || 'Category'}</text>
        <text x="14" y={paddingTop + chartInnerHeight / 2} transform={`rotate(-90 14 ${paddingTop + chartInnerHeight / 2})`} textAnchor="middle" className="font-arcade-mono text-[10px] fill-slate-600 font-bold">{yLabel || 'Value'}</text>
      </svg>

      {hoveredIdx !== null && (
        <div
          className="absolute z-20 pointer-events-none transform -translate-x-1/2 -translate-y-full -mt-2.5 bg-black text-white px-2 py-1 border-2 border-[#FFD200] font-arcade-mono text-[10px] font-bold tracking-wider retro-shadow-sm whitespace-nowrap"
          style={{
            left: `${(points[hoveredIdx].x / svgWidth) * 100}%`,
            top: `${(points[hoveredIdx].y / svgHeight) * 100}%`,
          }}
        >
          <div className="text-[#FFD200]">{points[hoveredIdx].label}</div>
          <div>
            {formatChartValue(points[hoveredIdx].val)} {unit || ''}
          </div>
        </div>
      )}
    </div>
  );
};
