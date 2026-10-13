import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { BarChart } from './BarChart';

afterEach(cleanup);

describe('BarChart', () => {
  it('exposes each bar with its label and value, and axis titles', () => {
    render(<BarChart labels={['RPG', 'Action']} values={[12, 30]} unit="copies" xLabel="Genre" yLabel="Copies" />);

    expect(screen.getByRole('group', { name: 'Copies by Genre' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'RPG: 12 copies' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'Action: 30 copies' })).toBeTruthy();
    expect(screen.getByText('Genre')).toBeTruthy();
    expect(screen.getByText('Copies')).toBeTruthy();
  });

  it('uses default axis labels when none are given', () => {
    render(<BarChart labels={['A']} values={[1]} />);
    expect(screen.getByRole('group', { name: 'Value by category' })).toBeTruthy();
    expect(screen.getByText('Category')).toBeTruthy();
  });

  it('shows a tooltip on hover and hides it on leave', () => {
    render(<BarChart labels={['RPG']} values={[1500]} unit="copies" />);
    const bar = screen.getByRole('img', { name: 'RPG: 1500 copies' });

    fireEvent.mouseEnter(bar);
    expect(screen.getByText(/^1\.5\s?K copies$/i)).toBeTruthy();

    fireEvent.mouseLeave(bar);
    expect(screen.queryByText(/^1\.5\s?K copies$/i)).toBeNull();
  });

  it('truncates long x labels', () => {
    const long = 'A'.repeat(30);
    render(<BarChart labels={[long]} values={[1]} />);
    expect(screen.getByText(`${'A'.repeat(23)}…`)).toBeTruthy();
  });

  it('renders axes without bars for empty data', () => {
    render(<BarChart labels={[]} values={[]} />);
    expect(screen.getByRole('group')).toBeTruthy();
    expect(screen.queryAllByRole('img')).toHaveLength(0);
  });

  it('treats missing values as zero', () => {
    render(<BarChart labels={['A', 'B']} values={[5]} />);
    expect(screen.getByRole('img', { name: 'B: 0' })).toBeTruthy();
  });
});
