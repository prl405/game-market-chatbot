import React, { useState } from 'react';
import { pie as d3pie, arc as d3arc } from 'd3-shape';
import { RETRO_COLORS } from './scales';

interface PieSlice {
  label: string;
  value: number;
}

interface RetroPieChartProps {
  slices: PieSlice[];
  unit?: string;
}

const SIZE = 220;
const RADIUS = SIZE / 2 - 10;

export const RetroPieChart: React.FC<RetroPieChartProps> = ({ slices, unit }) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const pieGenerator = d3pie<PieSlice>()
    .value((d) => d.value)
    .sort(null);
  const arcs = pieGenerator(slices);
  const arcGenerator = d3arc<ReturnType<typeof pieGenerator>[number]>().innerRadius(0).outerRadius(RADIUS);

  const total = slices.reduce((sum, s) => sum + s.value, 0);

  return (
    <div className="flex flex-col sm:flex-row items-center gap-4 pt-2">
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="w-48 h-48 sm:w-56 sm:h-56 shrink-0 overflow-visible"
      >
        <g transform={`translate(${SIZE / 2}, ${SIZE / 2})`}>
          {arcs.map((a, idx) => (
            <path
              key={idx}
              tabIndex={0}
              role="img"
              aria-label={`${a.data.label}: ${a.data.value}`}
              d={arcGenerator(a) || undefined}
              fill={RETRO_COLORS[idx % RETRO_COLORS.length]}
              stroke="#000"
              strokeWidth={2}
              className="cursor-pointer transition-transform hover:brightness-110"
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              onFocus={() => setHoveredIdx(idx)}
              onBlur={() => setHoveredIdx(null)}
            />
          ))}
        </g>
      </svg>

      <div className="flex flex-col gap-1.5 w-full">
        {slices.map((s, idx) => {
          const pct = total > 0 ? Math.round((s.value / total) * 1000) / 10 : 0;
          return (
            <div
              key={idx}
              tabIndex={0}
              role="img"
              aria-label={`${s.label}: ${s.value} ${unit || ''}, ${pct}%`}
              className={`flex cursor-pointer items-center gap-1.5 ${hoveredIdx === idx ? 'brightness-110' : ''}`}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              onFocus={() => setHoveredIdx(idx)}
              onBlur={() => setHoveredIdx(null)}
            >
              <div
                className="w-3 h-3 border border-black shrink-0"
                style={{ backgroundColor: RETRO_COLORS[idx % RETRO_COLORS.length] }}
              />
              <span className="min-w-0 flex-1 break-words font-arcade-mono text-[11px] font-bold text-black uppercase">
                {s.label}
              </span>
              <span className="shrink-0 font-arcade-mono text-[11px] text-slate-500 tabular-nums">
                {s.value} {unit || ''} ({pct}%)
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
