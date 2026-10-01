/**
 * Retro-styled chart dispatcher for the backend's chart_spec.
 *
 * Maps chart_spec (chart_type, data, x_field, y_field, title) onto one of
 * D3-backed chart bodies, all sharing the same retro header/border
 * frame. See src/game_market_chatbot/tools/chart_spec.py for the spec shape.
 */

import React from 'react';
import type { ChartSpec } from '../types';
import { BarChart } from './charts/BarChart';
import { LineChart } from './charts/LineChart';
import { ScatterChart } from './charts/ScatterChart';
import { PieChart } from './charts/PieChart';
import { HistogramChart } from './charts/HistogramChart';
import { formatChartLabel } from './charts/scales';

interface ChartRendererProps {
  data: ChartSpec;
}

export const ChartRenderer: React.FC<ChartRendererProps> = ({ data: spec }) => {
  const { chart_type, data, x_field, y_field, title } = spec;

  const labels = data.map((row) => formatChartLabel(String(row[x_field] ?? '')));
  const values = data.map((row) => Number(row[y_field] ?? 0));
  const displayXField = formatChartLabel(x_field);
  const displayYField = formatChartLabel(y_field);

  return (
    <div className="my-5 border-2 border-black bg-[#FAFBFD] p-3 sm:p-4 retro-shadow-sm">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2 pb-2.5 border-b-2 border-black">
        <span className="font-arcade-mono font-bold text-xs sm:text-sm text-black tracking-wider uppercase">
          {title}
        </span>
      </div>

      {chart_type === 'bar' && <BarChart labels={labels} values={values} xLabel={displayXField} yLabel={displayYField} />}
      {chart_type === 'line' && <LineChart labels={labels} values={values} xLabel={displayXField} yLabel={displayYField} />}
      {chart_type === 'scatter' && (
        <ScatterChart
          points={data.map((row) => ({ x: Number(row[x_field] ?? 0), y: Number(row[y_field] ?? 0) }))}
          xLabel={displayXField}
          yLabel={displayYField}
        />
      )}
      {chart_type === 'pie' && (
        <PieChart slices={data.map((row) => ({ label: formatChartLabel(String(row[x_field] ?? '')), value: Number(row[y_field] ?? 0) }))} />
      )}
      {chart_type === 'histogram' && spec.x_end_field && (
        <HistogramChart
          bins={data.map((row) => ({
            start: Number(row[x_field]),
            end: Number(row[spec.x_end_field!]),
            count: Number(row[y_field]),
          }))}
          xLabel={displayXField}
          yLabel={displayYField}
        />
      )}

      <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-slate-300 flex-wrap gap-2">
        <div className="font-arcade-mono text-[10px] text-slate-500 italic">
          X: {displayXField} &nbsp;/&nbsp; Y: {displayYField}
        </div>
      </div>
    </div>
  );
};

