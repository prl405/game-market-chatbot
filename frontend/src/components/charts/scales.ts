import { scaleBand, scaleLinear } from 'd3-scale';
import { max as d3max, min as d3min } from 'd3-array';

// Shared retro palette — single-series charts use the first color.
export const RETRO_COLORS = ['#2B66FF', '#FFD200', '#A855F7', '#22C55E', '#EF4444'];

export const CHART_DIMENSIONS = {
  svgWidth: 600,
  svgHeight: 220,
  paddingLeft: 45,
  paddingRight: 20,
  paddingTop: 20,
  paddingBottom: 30,
};

export const chartInnerWidth =
  CHART_DIMENSIONS.svgWidth - CHART_DIMENSIONS.paddingLeft - CHART_DIMENSIONS.paddingRight;
export const chartInnerHeight =
  CHART_DIMENSIONS.svgHeight - CHART_DIMENSIONS.paddingTop - CHART_DIMENSIONS.paddingBottom;

/** Rounds a raw max value up to a visually "neat" upper bound for axis scaling. */
export function niceMax(rawMax: number): number {
  const safeMax = Math.max(rawMax, 10);
  const magnitude = Math.pow(10, Math.floor(Math.log10(safeMax)));
  return Math.ceil(safeMax / magnitude) * magnitude || 100;
}

export function buildYTicks(maxVal: number): number[] {
  return [
    maxVal,
    Math.round(maxVal * 0.75 * 10) / 10,
    Math.round(maxVal * 0.5 * 10) / 10,
    Math.round(maxVal * 0.25 * 10) / 10,
    0,
  ];
}

export function buildBandScale(labels: string[]) {
  return scaleBand<string>()
    .domain(labels)
    .range([CHART_DIMENSIONS.paddingLeft, CHART_DIMENSIONS.svgWidth - CHART_DIMENSIONS.paddingRight])
    .padding(0.3);
}

export function buildYScale(maxVal: number) {
  return scaleLinear()
    .domain([0, maxVal])
    .range([CHART_DIMENSIONS.paddingTop + chartInnerHeight, CHART_DIMENSIONS.paddingTop]);
}

export function buildXPointScale(labels: string[]) {
  return scaleLinear()
    .domain([0, Math.max(labels.length - 1, 1)])
    .range([CHART_DIMENSIONS.paddingLeft, CHART_DIMENSIONS.svgWidth - CHART_DIMENSIONS.paddingRight]);
}

export function buildLinearDomainScale(values: number[], range: [number, number], padFraction = 0.1) {
  const lo = d3min(values) ?? 0;
  const hi = d3max(values) ?? 1;
  const span = hi - lo || 1;
  return scaleLinear()
    .domain([lo - span * padFraction, hi + span * padFraction])
    .range(range);
}
