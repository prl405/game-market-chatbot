import React, { useState } from 'react';
import { scaleLinear } from 'd3-scale';
import {
  CHART_DIMENSIONS,
  RETRO_COLORS,
  buildYScale,
  buildYTicks,
  chartInnerHeight,
  chartInnerWidth,
  formatChartValue,
  niceMax,
} from './scales';

interface HistogramBin {
  start: number;
  end: number;
  count: number;
}

interface RetroHistogramChartProps {
  bins: HistogramBin[];
  xLabel: string;
  yLabel: string;
}

export const RetroHistogramChart: React.FC<RetroHistogramChartProps> = ({ bins, xLabel, yLabel }) => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const { svgWidth, svgHeight, paddingLeft, paddingRight, paddingTop } = CHART_DIMENSIONS;
  const minimum = bins[0]?.start ?? 0;
  const maximum = bins[bins.length - 1]?.end ?? 1;
  const xScale = scaleLinear()
    .domain([minimum, maximum])
    .range([paddingLeft, svgWidth - paddingRight]);
  const maxCount = niceMax(Math.max(...bins.map((bin) => bin.count), 0));
  const yScale = buildYScale(maxCount);
  const ticks = buildYTicks(maxCount);

  return (
    <div className="relative w-full overflow-x-auto select-none pt-2">
      <svg
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        className="w-full min-w-[560px] h-auto overflow-visible"
        role="group"
        aria-label={`${yLabel} by ${xLabel} range`}
      >
        {ticks.map((tick) => {
          const y = yScale(tick);
          return (
            <g key={tick}>
              <line x1={paddingLeft} y1={y} x2={svgWidth - paddingRight} y2={y} stroke="#CBD5E1" strokeWidth="1" strokeDasharray="3 3" />
              <text x={paddingLeft - 7} y={y + 3} textAnchor="end" className="font-arcade-mono text-[9px] fill-slate-500">{formatChartValue(tick)}</text>
            </g>
          );
        })}
        {[0, 0.25, 0.5, 0.75, 1].map((fraction) => {
          const value = minimum + (maximum - minimum) * fraction;
          const x = xScale(value);
          return (
            <g key={fraction}>
              <line x1={x} y1={paddingTop} x2={x} y2={paddingTop + chartInnerHeight} stroke="#CBD5E1" strokeWidth="1" strokeDasharray="3 3" />
              <text x={x} y={paddingTop + chartInnerHeight + 15} textAnchor="middle" className="font-arcade-mono text-[9px] fill-slate-500">{formatChartValue(value)}</text>
            </g>
          );
        })}
        <line x1={paddingLeft} y1={paddingTop + chartInnerHeight} x2={svgWidth - paddingRight} y2={paddingTop + chartInnerHeight} stroke="#000" strokeWidth="2" />
        <line x1={paddingLeft} y1={paddingTop} x2={paddingLeft} y2={paddingTop + chartInnerHeight} stroke="#000" strokeWidth="2" />
        {bins.map((bin, index) => {
          const x = xScale(bin.start);
          const y = yScale(bin.count);
          const width = Math.max(0, xScale(bin.end) - x);
          const height = paddingTop + chartInnerHeight - y;
          return (
            <rect
              key={`${bin.start}-${bin.end}`}
              x={x}
              y={y}
              width={width}
              height={height}
              fill={RETRO_COLORS[0]}
              stroke="#000"
              strokeWidth="1.5"
              tabIndex={0}
              role="img"
              aria-label={`${formatChartValue(bin.start)} to ${formatChartValue(bin.end)}: ${bin.count} ${yLabel}`}
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
              onFocus={() => setHoveredIndex(index)}
              onBlur={() => setHoveredIndex(null)}
            />
          );
        })}
        <text x={paddingLeft + chartInnerWidth / 2} y={svgHeight - 7} textAnchor="middle" className="font-arcade-mono text-[10px] fill-slate-600 font-bold">{xLabel}</text>
        <text x="14" y={paddingTop + chartInnerHeight / 2} transform={`rotate(-90 14 ${paddingTop + chartInnerHeight / 2})`} textAnchor="middle" className="font-arcade-mono text-[10px] fill-slate-600 font-bold">{yLabel}</text>
      </svg>
      {hoveredIndex !== null && (
        <div
          className="absolute z-20 pointer-events-none transform -translate-x-1/2 -translate-y-full -mt-2.5 bg-black text-white px-2 py-1 border-2 border-[#FFD200] font-arcade-mono text-[10px] font-bold whitespace-nowrap"
          style={{
            left: `${(xScale((bins[hoveredIndex].start + bins[hoveredIndex].end) / 2) / svgWidth) * 100}%`,
            top: `${(yScale(bins[hoveredIndex].count) / svgHeight) * 100}%`,
          }}
        >
          {formatChartValue(bins[hoveredIndex].start)} to {formatChartValue(bins[hoveredIndex].end)}: {bins[hoveredIndex].count}
        </div>
      )}
    </div>
  );
};