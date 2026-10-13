import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { PromptPresetsModal } from './PromptPresetsModal';

afterEach(cleanup);

describe('PromptPresetsModal', () => {
  it('renders nothing when closed', () => {
    render(<PromptPresetsModal isOpen={false} onClose={vi.fn()} onSelectPreset={vi.fn()} />);
    expect(screen.queryByText('TACTICAL PROMPT PRESETS')).toBeNull();
    expect(screen.queryByRole('button')).toBeNull();
  });

  it('shows the header and a list of selectable presets when open', () => {
    render(<PromptPresetsModal isOpen onClose={vi.fn()} onSelectPreset={vi.fn()} />);
    expect(screen.getByText('TACTICAL PROMPT PRESETS')).toBeTruthy();
    expect(screen.getByRole('button', { name: /Top 10 Games by Copies Sold/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /Median Game Price/i })).toBeTruthy();
  });

  it('passes the preset prompt to the callback and closes', () => {
    const onSelectPreset = vi.fn();
    const onClose = vi.fn();
    render(<PromptPresetsModal isOpen onClose={onClose} onSelectPreset={onSelectPreset} />);
    fireEvent.click(screen.getByRole('button', { name: /Median Game Price/i }));
    expect(onSelectPreset).toHaveBeenCalledWith('What is the median price of games in the dataset?');
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('closes without selecting via the close button', () => {
    const onSelectPreset = vi.fn();
    const onClose = vi.fn();
    render(<PromptPresetsModal isOpen onClose={onClose} onSelectPreset={onSelectPreset} />);
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[0]); // header close button precedes the presets
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onSelectPreset).not.toHaveBeenCalled();
  });
});
