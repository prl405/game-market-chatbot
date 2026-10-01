import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { Message } from '../types';
import { AssistantMessage } from './AssistantMessage';
import { ChartRenderer } from './ChartSpecRenderer';
import { parseResponseBlocks } from '../services/llmClient';
import type { ChartSpec } from '../types';

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
    expect(screen.getByRole('group', { name: 'Copies by Genre' })).toBeTruthy();
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

    expect(screen.getByRole('group', { name: 'Count by Bin Start range' })).toBeTruthy();
    expect(screen.getByRole('img', { name: '0 to 5: 3 Count' })).toBeTruthy();
    expect(screen.getByRole('img', { name: '5 to 10: 7 Count' })).toBeTruthy();
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

describe('ChartRenderer labels', () => {
  it.each([
    {
      chart_type: 'bar',
      data: [{ release_type: 'role_playing', total_copies_sold: 12 }],
      x_field: 'release_type',
      y_field: 'total_copies_sold',
    },
    {
      chart_type: 'line',
      data: [{ release_type: 'role_playing', total_copies_sold: 12 }],
      x_field: 'release_type',
      y_field: 'total_copies_sold',
    },
    {
      chart_type: 'scatter',
      data: [{ average_price: 20, total_copies_sold: 12 }],
      x_field: 'average_price',
      y_field: 'total_copies_sold',
    },
    {
      chart_type: 'pie',
      data: [{ release_type: 'role_playing', total_copies_sold: 12 }],
      x_field: 'release_type',
      y_field: 'total_copies_sold',
    },
    {
      chart_type: 'histogram',
      data: [{ bin_start: 0, bin_end: 5, count: 3 }],
      x_field: 'bin_start',
      x_end_field: 'bin_end',
      y_field: 'count',
    },
  ] satisfies ChartSpec[])('formats $chart_type field names for display', (chart) => {
    const { container } = render(
      <ChartRenderer data={{ ...chart, title: 'Chart title' }} />,
    );
    const renderedText = container.textContent ?? '';

    expect(renderedText).not.toMatch(/\w_\w/);
    expect(renderedText).toContain(chart.chart_type === 'histogram' ? 'Bin Start' :
      chart.chart_type === 'scatter' ? 'Average Price' : 'Release Type');
    expect(renderedText).toContain(chart.chart_type === 'histogram' ? 'Count' : 'Total Copies Sold');
    if (chart.chart_type === 'bar' || chart.chart_type === 'line' || chart.chart_type === 'pie') {
      expect(renderedText).toContain('Role Playing');
    }
  });
});