import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { Message } from '../types';
import { AssistantMessage } from './AssistantMessage';
import { parseResponseBlocks } from '../services/llmClient';

const message = (contentBlocks: NonNullable<Message['contentBlocks']>): Message => ({
  id: 'assistant-test',
  role: 'assistant',
  content: contentBlocks
    .filter((block) => block.type === 'markdown')
    .map((block) => block.content)
    .join('\n\n'),
  contentBlocks,
  timestamp: 'NOW',
});

describe('AssistantMessage mixed content', () => {
  it('renders GFM tables and charts in their supplied order', () => {
    const { container } = render(<AssistantMessage message={message([
      { type: 'markdown', content: 'Before the chart.\n\n| Genre | Copies |\n| --- | ---: |\n| RPG | 12 |' },
      {
        type: 'chart',
        chart: {
          chart_type: 'bar',
          data: [{ genre: 'RPG', copies: 12 }],
          x_field: 'genre',
          y_field: 'copies',
          title: 'Copies by genre',
        },
      },
      { type: 'markdown', content: 'After the chart.' },
    ])} />);

    expect(screen.getByRole('table')).toBeTruthy();
    const header = screen.getByRole('columnheader', { name: 'Genre' });
    expect(header.className).toContain('border-black');
    expect(header.className).toContain('bg-[#2B66FF]');
    expect(header.className).toContain('text-white');
    expect(container.querySelector('td')?.className).toContain('border-black');
    expect(screen.getAllByText('RPG').length).toBeGreaterThan(0);
    expect(screen.getByText('Copies by genre')).toBeTruthy();
    expect(screen.getByRole('group', { name: 'copies by genre' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'RPG: 12' })).toBeTruthy();
    const text = container.textContent ?? '';
    expect(text.indexOf('Before the chart.')).toBeLessThan(text.indexOf('Copies by genre'));
    expect(text.indexOf('Copies by genre')).toBeLessThan(text.indexOf('After the chart.'));
  });

  it('does not interpret raw HTML in model Markdown', () => {
    const { container } = render(<AssistantMessage message={message([
      { type: 'markdown', content: '<img src="x" onerror="alert(1)" />' },
    ])} />);

    expect(container.querySelector('img')).toBeNull();
  });

  it('replaces malformed chart blocks with a readable fallback', () => {
    expect(parseResponseBlocks([
      { type: 'chart', chart: { chart_type: 'bar', data: [], x_field: 'x', y_field: 'y', title: 'Invalid' } },
    ], '', null)).toEqual([
      { type: 'markdown', content: 'Chart unavailable: the chart data was invalid.' },
    ]);
  });

  it('renders histogram intervals with range labels and frequencies', () => {
    render(<AssistantMessage message={message([
      {
        type: 'chart',
        chart: {
          chart_type: 'histogram',
          data: [
            { bin_start: 0, bin_end: 5, count: 3 },
            { bin_start: 5, bin_end: 10, count: 7 },
          ],
          x_field: 'bin_start',
          x_end_field: 'bin_end',
          y_field: 'count',
          title: 'Score distribution',
        },
      },
    ])} />);

    expect(screen.getByRole('group', { name: 'count by bin_start range' })).toBeTruthy();
    expect(screen.getByRole('img', { name: '0 to 5: 3 count' })).toBeTruthy();
    expect(screen.getByRole('img', { name: '5 to 10: 7 count' })).toBeTruthy();
  });

  it('rejects overlapping histogram intervals with the readable fallback', () => {
    expect(parseResponseBlocks([
      {
        type: 'chart',
        chart: {
          chart_type: 'histogram',
          data: [
            { start: 0, end: 6, count: 3 },
            { start: 5, end: 10, count: 7 },
          ],
          x_field: 'start',
          x_end_field: 'end',
          y_field: 'count',
          title: 'Invalid histogram',
        },
      },
    ], '', null)).toEqual([
      { type: 'markdown', content: 'Chart unavailable: the chart data was invalid.' },
    ]);
  });
});