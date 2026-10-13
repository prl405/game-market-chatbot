import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Message } from '../types';
import { parseResponseBlocks, sendChatRequest, testBackendHealth } from './llmClient';

const config = { endpoint: 'http://localhost:8000/api/chat' };
const history: Message[] = [
  { id: '1', role: 'user', content: 'Top genres?', timestamp: 'NOW' },
];

const barSpec = {
  chart_type: 'bar',
  data: [{ genre: 'RPG', copies: 12 }],
  x_field: 'genre',
  y_field: 'copies',
  title: 'Copies by genre',
};

const mockFetch = (impl: () => Promise<unknown>) => {
  const fn = vi.fn(impl);
  vi.stubGlobal('fetch', fn);
  return fn;
};
const jsonResponse = (body: unknown, init: Partial<Response> = {}) =>
  Promise.resolve({ ok: true, status: 200, statusText: 'OK', json: async () => body, ...init });

afterEach(() => vi.unstubAllGlobals());

describe('parseResponseBlocks', () => {
  it('keeps valid markdown and chart blocks in order', () => {
    const blocks = parseResponseBlocks(
      [{ type: 'markdown', content: 'Hi' }, { type: 'chart', chart: barSpec }],
      'ignored',
      null,
    );
    expect(blocks).toEqual([
      { type: 'markdown', content: 'Hi' },
      { type: 'chart', chart: barSpec },
    ]);
  });

  it('replaces an invalid chart block with an unavailable notice', () => {
    const blocks = parseResponseBlocks(
      [{ type: 'chart', chart: { ...barSpec, data: [{ genre: 'RPG', copies: 'lots' }] } }],
      '',
      null,
    );
    expect(blocks).toEqual([
      { type: 'markdown', content: 'Chart unavailable: the chart data was invalid.' },
    ]);
  });

  it.each([
    ['unknown chart type', { ...barSpec, chart_type: 'radar' }],
    ['empty data', { ...barSpec, data: [] }],
    ['missing title', { ...barSpec, title: undefined }],
    ['missing x field in row', { ...barSpec, data: [{ copies: 1 }] }],
    ['negative pie value', { ...barSpec, chart_type: 'pie', data: [{ genre: 'A', copies: -1 }] }],
    ['non-numeric scatter x', { ...barSpec, chart_type: 'scatter', data: [{ genre: 'A', copies: 1 }] }],
    ['more than 50 rows', { ...barSpec, data: Array.from({ length: 51 }, () => ({ genre: 'A', copies: 1 })) }],
  ])('rejects a chart with %s', (_name, chart) => {
    const blocks = parseResponseBlocks([{ type: 'chart', chart }], '', null);
    expect(blocks).toHaveLength(1);
    expect(blocks[0]).toMatchObject({ type: 'markdown' });
  });

  it('accepts a well-formed histogram and rejects overlapping bins', () => {
    const histogram = {
      chart_type: 'histogram',
      x_field: 'start',
      x_end_field: 'end',
      y_field: 'count',
      title: 'Prices',
      data: [{ start: 0, end: 10, count: 3 }, { start: 10, end: 20, count: 5 }],
    };
    expect(parseResponseBlocks([{ type: 'chart', chart: histogram }], '', null)[0].type).toBe('chart');

    const overlapping = { ...histogram, data: [{ start: 0, end: 10, count: 3 }, { start: 5, end: 20, count: 5 }] };
    expect(parseResponseBlocks([{ type: 'chart', chart: overlapping }], '', null)[0].type).toBe('markdown');
  });

  it('drops non-object entries and falls back to text when nothing remains', () => {
    expect(parseResponseBlocks([null, 'x', 5], 'fallback text', null)).toEqual([
      { type: 'markdown', content: 'fallback text' },
    ]);
    expect(parseResponseBlocks([], '', null)).toEqual([]);
  });

  it('falls back to text plus a valid legacy chart when blocks is absent', () => {
    expect(parseResponseBlocks(undefined, 'Answer', barSpec)).toEqual([
      { type: 'markdown', content: 'Answer' },
      { type: 'chart', chart: barSpec },
    ]);
  });

  it('ignores an invalid legacy chart and returns nothing for empty text', () => {
    expect(parseResponseBlocks(undefined, '', { chart_type: 'bar' })).toEqual([]);
  });
});

describe('sendChatRequest', () => {
  it('posts role/content history and returns parsed response', async () => {
    const fetchMock = mockFetch(() =>
      jsonResponse({ text: 'Answer', chart_spec: barSpec, blocks: [{ type: 'markdown', content: 'Answer' }] }),
    );

    const result = await sendChatRequest(history, config);

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(config.endpoint);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({
      messages: [{ role: 'user', content: 'Top genres?' }],
    });
    expect(result).toEqual({
      content: 'Answer',
      chartSpec: barSpec,
      blocks: [{ type: 'markdown', content: 'Answer' }],
    });
  });

  it('tolerates a response missing text, chart_spec and blocks', async () => {
    mockFetch(() => jsonResponse({}));
    expect(await sendChatRequest(history, config)).toEqual({ content: '', chartSpec: null, blocks: [] });
  });

  it('throws with the HTTP status for non-ok responses', async () => {
    mockFetch(() => jsonResponse({}, { ok: false, status: 500, statusText: 'Server Error' }));
    await expect(sendChatRequest(history, config)).rejects.toThrow(
      'Python server returned status 500: Server Error',
    );
  });

  it('wraps network failures with a helpful message', async () => {
    mockFetch(() => Promise.reject(new Error('connection refused')));
    await expect(sendChatRequest(history, config)).rejects.toThrow(/Failed to connect.*connection refused/s);
  });

  it('propagates a malformed JSON body as an error', async () => {
    mockFetch(() =>
      Promise.resolve({ ok: true, status: 200, statusText: 'OK', json: async () => { throw new SyntaxError('bad json'); } }),
    );
    await expect(sendChatRequest(history, config)).rejects.toThrow('bad json');
  });
});

describe('testBackendHealth', () => {
  it('pings /health derived from the chat endpoint', async () => {
    const fetchMock = mockFetch(() => jsonResponse({}));
    const result = await testBackendHealth(config.endpoint);
    expect((fetchMock.mock.calls[0] as unknown as [string])[0]).toBe('http://localhost:8000/health');
    expect(result.success).toBe(true);
  });

  it('reports HTTP failures', async () => {
    mockFetch(() => jsonResponse({}, { ok: false, status: 503 }));
    expect(await testBackendHealth(config.endpoint)).toEqual({
      success: false,
      message: 'Backend responded with HTTP status 503',
    });
  });

  it('reports unreachable backends', async () => {
    mockFetch(() => Promise.reject(new Error('ECONNREFUSED')));
    const result = await testBackendHealth(config.endpoint);
    expect(result.success).toBe(false);
    expect(result.message).toContain('ECONNREFUSED');
  });
});
