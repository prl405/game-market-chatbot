/**
 * Retro-styled chart dispatcher for the backend's chart_spec.
 *
 * Maps chart_spec (chart_type, data, x_field, y_field, title) onto one of
 * four D3-backed chart bodies, all sharing the same retro header/border
 * frame. See src/game_market_chatbot/tools/chart_spec.py for the spec shape.
 */

import React from 'react';
import type { ChartSpec } from '../types';
import { RetroBarChart } from './charts/RetroBarChart';
import { RetroLineChart } from './charts/RetroLineChart';
import { RetroScatterChart } from './charts/RetroScatterChart';
import { RetroPieChart } from './charts/RetroPieChart';

interface RetroChartProps {
  data: ChartSpec;
}

export const RetroChart: React.FC<RetroChartProps> = ({ data: spec }) => {
  const { chart_type, data, x_field, y_field, title } = spec;

  const labels = data.map((row) => String(row[x_field] ?? ''));
  const values = data.map((row) => Number(row[y_field] ?? 0));

  return (
    <div className="my-5 border-2 border-black bg-[#FAFBFD] p-3 sm:p-4 retro-shadow-sm">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2 pb-2.5 border-b-2 border-black">
        <span className="font-arcade-mono font-bold text-xs sm:text-sm text-black tracking-wider uppercase">
          {title}
        </span>
      </div>

      {chart_type === 'bar' && <RetroBarChart labels={labels} values={values} />}
      {chart_type === 'line' && <RetroLineChart labels={labels} values={values} />}
      {chart_type === 'scatter' && (
        <RetroScatterChart
          points={data.map((row) => ({ x: Number(row[x_field] ?? 0), y: Number(row[y_field] ?? 0) }))}
        />
      )}
      {chart_type === 'pie' && (
        <RetroPieChart slices={data.map((row) => ({ label: String(row[x_field] ?? ''), value: Number(row[y_field] ?? 0) }))} />
      )}

      <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-slate-300 flex-wrap gap-2">
        <div className="font-arcade-mono text-[10px] text-slate-500 italic">
          X: {x_field} &nbsp;/&nbsp; Y: {y_field}
        </div>
      </div>
    </div>
  );
};

