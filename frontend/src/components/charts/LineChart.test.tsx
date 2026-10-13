import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { LineChart } from './LineChart';

afterEach(cleanup);

describe('LineChart', () => {
  it('exposes each point with label and value, and axis titles', () => {
    render(<LineChart labels={['2020', '2021', '2022']} values={[5, 15, 10]} unit="USD" xLabel="Year" yLabel="Revenue" />);

    expect(screen.getByRole('group', { name: 'Revenue over Year' })).toBeTruthy();
    expect(screen.getByRole('img', { name: '2020: 5 USD' })).toBeTruthy();
    expect(screen.getByRole('img', { name: '2021: 15 USD' })).toBeTruthy();
    expect(screen.getByRole('img', { name: '2022: 10 USD' })).toBeTruthy();
    expect(screen.getByText('Year')).toBeTruthy();
    expect(screen.getByText('Revenue')).toBeTruthy();
  });

  it('shows tooltip details on focus and hides on blur', () => {
    render(<LineChart labels={['Q1', 'Q2']} values={[3, 8]} unit="units" />);
    const point = screen.getByRole('img', { name: 'Q2: 8 units' });

    fireEvent.focus(point);
    expect(screen.getByText('8 units')).toBeTruthy();

    fireEvent.blur(point);
    expect(screen.queryByText('8 units')).toBeNull();
  });

  it('renders a single point without error', () => {
    render(<LineChart labels={['Only']} values={[4]} />);
    expect(screen.getByRole('img', { name: 'Only: 4' })).toBeTruthy();
  });

  it('renders axes without points for empty data', () => {
    render(<LineChart labels={[]} values={[]} />);
    expect(screen.getByRole('group', { name: 'Value over category' })).toBeTruthy();
    expect(screen.queryAllByRole('img')).toHaveLength(0);
  });

  it('thins x labels for many points but keeps the last one', () => {
    const labels = Array.from({ length: 30 }, (_, i) => `L${i}`);
    render(<LineChart labels={labels} values={labels.map((_, i) => i)} />);
    expect(screen.getByText('L0')).toBeTruthy();
    expect(screen.getByText('L29')).toBeTruthy();
    expect(screen.queryByText('L1')).toBeNull();
  });
});
