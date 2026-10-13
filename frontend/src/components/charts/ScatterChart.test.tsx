import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { ScatterChart } from './ScatterChart';

afterEach(cleanup);

describe('ScatterChart', () => {
  const points = [
    { x: 10, y: 20, label: 'Game A' },
    { x: 30, y: 5 },
  ];

  it('exposes each point with label, coordinates and units', () => {
    render(<ScatterChart points={points} xUnit="USD" yUnit="hrs" xLabel="Price" yLabel="Playtime" />);

    expect(screen.getByRole('group', { name: 'Playtime by Price' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'Game A: 10 USD, 20 hrs' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'Point 2: 30 USD, 5 hrs' })).toBeTruthy();
    expect(screen.getByText('Price')).toBeTruthy();
    expect(screen.getByText('Playtime')).toBeTruthy();
  });

  it('uses default axis labels', () => {
    render(<ScatterChart points={points} />);
    expect(screen.getByRole('group', { name: 'Y value by X value' })).toBeTruthy();
  });

  it('shows a tooltip with the point label and values on hover', () => {
    render(<ScatterChart points={points} xUnit="USD" yUnit="hrs" />);
    const dot = screen.getByRole('img', { name: 'Game A: 10 USD, 20 hrs' });

    fireEvent.mouseEnter(dot);
    expect(screen.getAllByText('Game A').length).toBeGreaterThan(0);
    expect(screen.getByText(/10 USD \/ 20 hrs/)).toBeTruthy();

    fireEvent.mouseLeave(dot);
    expect(screen.queryByText(/10 USD \/ 20 hrs/)).toBeNull();
  });

  it('renders a single point', () => {
    render(<ScatterChart points={[{ x: 1, y: 1 }]} />);
    expect(screen.getAllByRole('img')).toHaveLength(1);
  });

  it('renders axes without points for empty data', () => {
    render(<ScatterChart points={[]} />);
    expect(screen.getByRole('group')).toBeTruthy();
    expect(screen.queryAllByRole('img')).toHaveLength(0);
  });
});
