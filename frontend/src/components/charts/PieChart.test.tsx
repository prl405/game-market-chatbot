import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { PieChart } from './PieChart';

afterEach(cleanup);

describe('PieChart', () => {
  const slices = [
    { label: 'Indie', value: 25 },
    { label: 'AAA', value: 75 },
  ];

  it('lists each slice with its value and percentage', () => {
    render(<PieChart slices={slices} unit="games" />);

    expect(screen.getByRole('img', { name: 'Indie: 25 games, 25%' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'AAA: 75 games, 75%' })).toBeTruthy();
    expect(screen.getByText('25 games (25%)')).toBeTruthy();
    expect(screen.getByText('Indie')).toBeTruthy();
  });

  it('draws one accessible wedge per slice', () => {
    render(<PieChart slices={slices} />);
    expect(screen.getByRole('img', { name: 'Indie: 25' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'AAA: 75' })).toBeTruthy();
  });

  it('rounds percentages to one decimal place', () => {
    render(<PieChart slices={[{ label: 'A', value: 1 }, { label: 'B', value: 2 }]} />);
    expect(screen.getByText('1 (33.3%)')).toBeTruthy();
    expect(screen.getByText('2 (66.7%)')).toBeTruthy();
  });

  it('shows 0% for every slice when the total is zero', () => {
    render(<PieChart slices={[{ label: 'A', value: 0 }]} />);
    expect(screen.getByText('0 (0%)')).toBeTruthy();
  });

  it('renders nothing selectable for empty data', () => {
    render(<PieChart slices={[]} />);
    expect(screen.queryAllByRole('img')).toHaveLength(0);
  });

  it('remains interactive via focus without throwing', () => {
    render(<PieChart slices={slices} unit="games" />);
    const row = screen.getByRole('img', { name: 'Indie: 25 games, 25%' });
    fireEvent.focus(row);
    fireEvent.blur(row);
    expect(row).toBeTruthy();
  });
});
