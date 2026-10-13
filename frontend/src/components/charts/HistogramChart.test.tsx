import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { HistogramChart } from './HistogramChart';

afterEach(cleanup);

describe('HistogramChart', () => {
  const bins = [
    { start: 0, end: 10, count: 4 },
    { start: 10, end: 20, count: 9 },
  ];

  it('exposes each bin with its range and count, plus axis titles', () => {
    render(<HistogramChart bins={bins} xLabel="Price" yLabel="Games" />);

    expect(screen.getByRole('group', { name: 'Games by Price range' })).toBeTruthy();
    expect(screen.getByRole('img', { name: '0 to 10: 4 Games' })).toBeTruthy();
    expect(screen.getByRole('img', { name: '10 to 20: 9 Games' })).toBeTruthy();
    expect(screen.getByText('Price')).toBeTruthy();
    expect(screen.getByText('Games')).toBeTruthy();
  });

  it('shows and hides a tooltip for the hovered bin', () => {
    render(<HistogramChart bins={bins} xLabel="Price" yLabel="Games" />);
    const bin = screen.getByRole('img', { name: '10 to 20: 9 Games' });

    fireEvent.mouseEnter(bin);
    expect(screen.getByText('10 to 20: 9')).toBeTruthy();

    fireEvent.mouseLeave(bin);
    expect(screen.queryByText('10 to 20: 9')).toBeNull();
  });

  it('labels the x axis across the full range', () => {
    render(<HistogramChart bins={bins} xLabel="Price" yLabel="Games" />);
    expect(screen.getAllByText('0').length).toBeGreaterThan(0);
    expect(screen.getAllByText('10').length).toBeGreaterThan(0);
    expect(screen.getAllByText('20').length).toBeGreaterThan(0);
  });

  it('renders axes without bins for empty data', () => {
    render(<HistogramChart bins={[]} xLabel="Price" yLabel="Games" />);
    expect(screen.getByRole('group', { name: 'Games by Price range' })).toBeTruthy();
    expect(screen.queryAllByRole('img')).toHaveLength(0);
  });
});
