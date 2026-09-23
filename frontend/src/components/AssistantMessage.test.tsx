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
    expect(screen.getByRole('columnheader', { name: 'Genre' })).toBeTruthy();
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
});