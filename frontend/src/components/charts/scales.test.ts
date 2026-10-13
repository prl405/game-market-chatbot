import { describe, expect, it } from 'vitest';
import {
  CHART_DIMENSIONS,
  buildBandScale,
  buildLinearDomainScale,
  buildXPointScale,
  buildYScale,
  buildYTicks,
  chartInnerHeight,
  chartInnerWidth,
  chartLabelStride,
  formatChartLabel,
  formatChartValue,
  niceMax,
} from './scales';

describe('inner dimensions', () => {
  it('equal svg size minus padding', () => {
    expect(chartInnerWidth).toBe(600 - 68 - 24);
    expect(chartInnerHeight).toBe(300 - 28 - 106);
  });
});

describe('niceMax', () => {
  it.each([
    [0, 10],
    [-5, 10],
    [7, 10],
    [10, 10],
    [11, 20],
    [87, 90],
    [100, 100],
    [101, 200],
    [4321, 5000],
  ])('rounds %d up to %d', (input, expected) => {
    expect(niceMax(input)).toBe(expected);
  });
});

describe('buildYTicks', () => {
  it('returns max, three quarters, half, quarter and zero', () => {
    expect(buildYTicks(100)).toEqual([100, 75, 50, 25, 0]);
  });

  it('rounds to one decimal place', () => {
    expect(buildYTicks(10)).toEqual([10, 7.5, 5, 2.5, 0]);
    expect(buildYTicks(1)).toEqual([1, 0.8, 0.5, 0.3, 0]);
  });
});

describe('buildBandScale', () => {
  it('has no bands for empty labels', () => {
    expect(buildBandScale([]).domain()).toEqual([]);
  });

  it('positions bands left to right within the padded range', () => {
    const scale = buildBandScale(['a', 'b', 'c']);
    const first = scale('0')!;
    const last = scale('2')!;
    expect(first).toBeGreaterThanOrEqual(CHART_DIMENSIONS.paddingLeft);
    expect(last + scale.bandwidth()).toBeLessThanOrEqual(CHART_DIMENSIONS.svgWidth - CHART_DIMENSIONS.paddingRight);
    expect(scale('1')!).toBeGreaterThan(first);
    expect(scale.bandwidth()).toBeGreaterThan(0);
  });

  it('handles a single label', () => {
    const scale = buildBandScale(['only']);
    expect(scale('0')).toBeDefined();
    expect(scale('1')).toBeUndefined();
  });
});

describe('formatChartValue', () => {
  it('formats small numbers plainly with at most one decimal', () => {
    expect(formatChartValue(0)).toBe('0');
    expect(formatChartValue(12)).toBe('12');
    expect(formatChartValue(1.26)).toBe('1.3');
  });

  it('uses compact notation at 1000 and above, including negatives', () => {
    expect(formatChartValue(1500)).toMatch(/^1\.5\s?K$/i);
    expect(formatChartValue(-2000)).toMatch(/^-2\s?K$/i);
    expect(formatChartValue(999)).toBe('999');
  });
});

describe('formatChartLabel', () => {
  it('replaces underscores, collapses whitespace and title-cases words', () => {
    expect(formatChartLabel('avg_price_usd')).toBe('Avg Price Usd');
    expect(formatChartLabel('  total   copies ')).toBe('Total Copies');
  });

  it('handles an empty string', () => {
    expect(formatChartLabel('')).toBe('');
  });
});

describe('chartLabelStride', () => {
  it.each([
    [0, 1],
    [1, 1],
    [12, 1],
    [13, 2],
    [24, 2],
    [25, 3],
    [50, 5],
  ])('count %d gives stride %d', (count, stride) => {
    expect(chartLabelStride(count)).toBe(stride);
  });
});

describe('buildYScale', () => {
  it('maps 0 to the baseline and max to the top padding', () => {
    const scale = buildYScale(100);
    expect(scale(0)).toBe(CHART_DIMENSIONS.paddingTop + chartInnerHeight);
    expect(scale(100)).toBe(CHART_DIMENSIONS.paddingTop);
    expect(scale(50)).toBe(CHART_DIMENSIONS.paddingTop + chartInnerHeight / 2);
  });
});

describe('buildXPointScale', () => {
  it('spans the padded width from first to last label', () => {
    const scale = buildXPointScale(['a', 'b', 'c']);
    expect(scale(0)).toBe(CHART_DIMENSIONS.paddingLeft);
    expect(scale(2)).toBe(CHART_DIMENSIONS.svgWidth - CHART_DIMENSIONS.paddingRight);
  });

  it('does not divide by zero for empty or single labels', () => {
    for (const labels of [[], ['x']]) {
      const scale = buildXPointScale(labels);
      expect(scale(0)).toBe(CHART_DIMENSIONS.paddingLeft);
      expect(Number.isFinite(scale(1))).toBe(true);
    }
  });
});

describe('buildLinearDomainScale', () => {
  it('pads the domain by the given fraction', () => {
    const scale = buildLinearDomainScale([0, 100], [0, 100]);
    expect(scale.domain()).toEqual([-10, 110]);
    expect(scale(-10)).toBe(0);
    expect(scale(110)).toBe(100);
  });

  it('respects a custom pad fraction', () => {
    expect(buildLinearDomainScale([0, 10], [0, 1], 0).domain()).toEqual([0, 10]);
  });

  it('gives a non-degenerate domain for a single value', () => {
    const [lo, hi] = buildLinearDomainScale([5], [0, 100]).domain();
    expect(lo).toBeLessThan(5);
    expect(hi).toBeGreaterThan(5);
  });

  it('falls back to a finite domain for empty input', () => {
    const [lo, hi] = buildLinearDomainScale([], [0, 100]).domain();
    expect(Number.isFinite(lo)).toBe(true);
    expect(hi).toBeGreaterThan(lo);
  });
});
