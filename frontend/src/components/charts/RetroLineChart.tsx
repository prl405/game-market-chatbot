import React, { useState } from 'react';
import { line as d3line } from 'd3-shape';
import {
  CHART_DIMENSIONS,
  RETRO_COLORS,
  buildXPointScale,
  buildYScale,
  buildYTicks,
  chartInnerHeight,
  niceMax,
} from './scales';

interface RetroLineChartProps {
  labels: string[];
  values: number[];
  color?: string;
  unit?: string;
}

export const RetroLineChart: React.FC<RetroLineChartProps> = ({ labels, values, color, unit }) => {
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
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
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

        {labels.map((lbl, idx) => (
          <text
            key={idx}
            x={xScale(idx)}
            y={paddingTop + chartInnerHeight + 16}
            textAnchor="middle"
            className="font-arcade-mono text-[9px] sm:text-[10px] fill-black font-bold uppercase"
          >
            {lbl}
          </text>
        ))}
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
            {points[hoveredIdx].val} {unit || ''}
          </div>
        </div>
      )}
    </div>
  );
};
