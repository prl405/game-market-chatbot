import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Session } from '../types';
import { Sidebar } from './Sidebar';

afterEach(cleanup);

const session = (id: string, title: string): Session => ({
  id,
  title,
  sessionCode: '#1',
  bannerTitle: 'B',
  bannerSubtitle: 'S',
  messages: [],
  outline: [],
  createdAt: 'NOW',
});

const two = [session('a', 'CHALLENGE_ONE.EXE'), session('b', 'second_chat')];

const setup = (over: Partial<React.ComponentProps<typeof Sidebar>> = {}) => {
  const props = {
    sessions: two,
    activeSessionId: 'a',
    onSelectSession: vi.fn(),
    onNewGame: vi.fn(),
    onDeleteSession: vi.fn(),
    isOpen: true,
    ...over,
  };
  render(<Sidebar {...props} />);
  return props;
};

describe('Sidebar', () => {
  it('renders nothing when closed', () => {
    setup({ isOpen: false });
    expect(screen.queryByText('NEW CHAT')).toBeNull();
    expect(screen.queryByText('CURRENT CHATS')).toBeNull();
  });

  it('lists sessions with .EXE stripped and underscores replaced', () => {
    setup();
    expect(screen.getByRole('button', { name: 'CHALLENGE ONE' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'second chat' })).toBeTruthy();
  });

  it('selects a session and starts a new chat', () => {
    const p = setup();
    fireEvent.click(screen.getByRole('button', { name: 'second chat' }));
    expect(p.onSelectSession).toHaveBeenCalledWith('b');
    fireEvent.click(screen.getByRole('button', { name: /new chat/i }));
    expect(p.onNewGame).toHaveBeenCalledTimes(1);
  });

  it('deletes a session without selecting it', () => {
    const p = setup();
    const del = screen.getAllByRole('button', { name: 'Delete Run' });
    expect(del).toHaveLength(2);
    fireEvent.click(del[1]);
    expect(p.onDeleteSession).toHaveBeenCalledWith('b');
    expect(p.onSelectSession).not.toHaveBeenCalled();
  });

  it('hides delete controls when only one session exists', () => {
    setup({ sessions: [two[0]] });
    expect(screen.queryByRole('button', { name: 'Delete Run' })).toBeNull();
  });

  it('shows an empty list with only the new chat button', () => {
    setup({ sessions: [] });
    expect(screen.getByRole('button', { name: /new chat/i })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Delete Run' })).toBeNull();
  });

  it('collapses via the toggle button when provided', () => {
    const onToggleSidebar = vi.fn();
    setup({ onToggleSidebar });
    fireEvent.click(screen.getByRole('button', { name: 'Collapse Sidebar' }));
    expect(onToggleSidebar).toHaveBeenCalledTimes(1);
  });

  it('omits the collapse button without a toggle handler', () => {
    setup();
    expect(screen.queryByRole('button', { name: 'Collapse Sidebar' })).toBeNull();
  });
});
