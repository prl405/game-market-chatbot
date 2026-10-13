import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { OutlineItem } from '../types';
import { OutlinePanel } from './OutlinePanel';

afterEach(cleanup);

const items: OutlineItem[] = [
  { id: '1', title: 'Top games', messageId: 'm1' },
  { id: '2', title: 'Genre share', messageId: 'm2' },
];

describe('OutlinePanel', () => {
  it('renders nothing when closed', () => {
    render(<OutlinePanel items={items} onItemClick={vi.fn()} isOpen={false} />);
    expect(screen.queryByText('OUTLINE')).toBeNull();
    expect(screen.queryByText('Top games')).toBeNull();
  });

  it('lists outline items in order and reports the clicked item', () => {
    const onItemClick = vi.fn();
    render(<OutlinePanel items={items} onItemClick={onItemClick} isOpen />);
    expect(screen.getByText('OUTLINE')).toBeTruthy();
    const buttons = screen.getAllByRole('button', { name: /top games|genre share/i });
    expect(buttons.map((b) => b.textContent)).toEqual(['Top games', 'Genre share']);
    fireEvent.click(buttons[1]);
    expect(onItemClick).toHaveBeenCalledWith(items[1]);
    expect(screen.queryByText('No sections detected yet.')).toBeNull();
  });

  it('shows the empty message when there are no items', () => {
    render(<OutlinePanel items={[]} onItemClick={vi.fn()} isOpen />);
    expect(screen.getByText('No sections detected yet.')).toBeTruthy();
  });

  it('collapses via the toggle button when provided', () => {
    const onToggleOutline = vi.fn();
    render(<OutlinePanel items={items} onItemClick={vi.fn()} isOpen onToggleOutline={onToggleOutline} />);
    fireEvent.click(screen.getByRole('button', { name: 'Collapse Outline' }));
    expect(onToggleOutline).toHaveBeenCalledTimes(1);
  });

  it('omits the collapse button without a toggle handler', () => {
    render(<OutlinePanel items={items} onItemClick={vi.fn()} isOpen />);
    expect(screen.queryByRole('button', { name: 'Collapse Outline' })).toBeNull();
  });
});
