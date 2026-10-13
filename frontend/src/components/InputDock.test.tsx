import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { InputDock } from './InputDock';

afterEach(cleanup);

const box = () => screen.getByRole('textbox') as HTMLTextAreaElement;
const send = () => screen.getByRole('button', { name: /send/i }) as HTMLButtonElement;

describe('InputDock', () => {
  it('sends trimmed text via the SEND button and clears the input', () => {
    const onSend = vi.fn();
    render(<InputDock onSendMessage={onSend} isLoading={false} />);
    fireEvent.change(box(), { target: { value: '  top games  ' } });
    fireEvent.click(send());
    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend).toHaveBeenCalledWith('top games');
    expect(box().value).toBe('');
  });

  it('sends on Enter but not on Shift+Enter', () => {
    const onSend = vi.fn();
    render(<InputDock onSendMessage={onSend} isLoading={false} />);
    fireEvent.change(box(), { target: { value: 'hello' } });
    fireEvent.keyDown(box(), { key: 'Enter', shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
    expect(box().value).toBe('hello');
    fireEvent.keyDown(box(), { key: 'Enter' });
    expect(onSend).toHaveBeenCalledWith('hello');
  });

  it('keeps SEND disabled and ignores Enter for empty or whitespace input', () => {
    const onSend = vi.fn();
    render(<InputDock onSendMessage={onSend} isLoading={false} />);
    expect(send().disabled).toBe(true);
    fireEvent.change(box(), { target: { value: '   ' } });
    expect(send().disabled).toBe(true);
    fireEvent.keyDown(box(), { key: 'Enter' });
    expect(onSend).not.toHaveBeenCalled();
  });

  it('disables the input and SEND while loading', () => {
    const onSend = vi.fn();
    render(<InputDock onSendMessage={onSend} isLoading />);
    expect(box().disabled).toBe(true);
    expect(send().disabled).toBe(true);
    fireEvent.keyDown(box(), { key: 'Enter' });
    expect(onSend).not.toHaveBeenCalled();
  });

  it('opens presets from the presets button, tolerating a missing handler', () => {
    const onOpen = vi.fn();
    const { rerender } = render(<InputDock onSendMessage={vi.fn()} isLoading={false} onOpenPresets={onOpen} />);
    fireEvent.click(screen.getByRole('button', { name: /prompt presets/i }));
    expect(onOpen).toHaveBeenCalledTimes(1);
    rerender(<InputDock onSendMessage={vi.fn()} isLoading={false} />);
    expect(() => fireEvent.click(screen.getByRole('button', { name: /prompt presets/i }))).not.toThrow();
  });
});
