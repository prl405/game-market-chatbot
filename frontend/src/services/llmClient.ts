import type { BackendConfig, ChartSpec, Message, ResponseBlock } from '../types';

export const DEFAULT_BACKEND_CONFIG: BackendConfig = {
  endpoint: 'http://localhost:8000/api/chat',
};

export interface ChatResponse {
  content: string;
  chartSpec: ChartSpec | null;
  blocks: ResponseBlock[];
}

function isChartSpec(value: unknown): value is ChartSpec {
  if (!value || typeof value !== 'object') return false;
  const spec = value as Partial<ChartSpec>;
  if (!['bar', 'line', 'scatter', 'pie', 'histogram'].includes(String(spec.chart_type))) return false;
  if (!Array.isArray(spec.data) || spec.data.length === 0 || spec.data.length > 50) return false;
  if (typeof spec.x_field !== 'string' || typeof spec.y_field !== 'string') return false;
  if (!spec.x_field || !spec.y_field || typeof spec.title !== 'string') return false;

  if (spec.chart_type === 'histogram') {
    if (typeof spec.x_end_field !== 'string' || !spec.x_end_field || spec.data.length > 20) return false;
    let previousEnd = -Infinity;
    return spec.data.every((row) => {
      if (!row || typeof row !== 'object') return false;
      const values = row as Record<string, unknown>;
      const lower = values[spec.x_field!];
      const upper = values[spec.x_end_field!];
      const count = values[spec.y_field!];
      if (
        typeof lower !== 'number' || !Number.isFinite(lower) ||
        typeof upper !== 'number' || !Number.isFinite(upper) ||
        typeof count !== 'number' || !Number.isFinite(count) ||
        lower >= upper || count < 0 || lower < previousEnd
      ) return false;
      previousEnd = upper;
      return true;
    });
  }

  return spec.data.every((row) => {
    if (!row || typeof row !== 'object') return false;
    const values = row as Record<string, unknown>;
    if (!Object.hasOwn(values, spec.x_field!) || !Object.hasOwn(values, spec.y_field!)) return false;
    const x = values[spec.x_field!];
    const y = values[spec.y_field!];
    return typeof y === 'number' && Number.isFinite(y) &&
      (spec.chart_type !== 'scatter' || (typeof x === 'number' && Number.isFinite(x))) &&
      (spec.chart_type !== 'pie' || y >= 0);
  });
}

export function parseResponseBlocks(value: unknown, text: string, legacyChart: unknown): ResponseBlock[] {
  if (Array.isArray(value)) {
    const blocks = value.flatMap((block): ResponseBlock[] => {
      if (!block || typeof block !== 'object') return [];
      const candidate = block as Record<string, unknown>;
      if (candidate.type === 'markdown' && typeof candidate.content === 'string') {
        return [{ type: 'markdown', content: candidate.content }];
      }
      if (candidate.type === 'chart' && isChartSpec(candidate.chart)) {
        return [{ type: 'chart', chart: candidate.chart }];
      }
      return [{ type: 'markdown', content: 'Chart unavailable: the chart data was invalid.' }];
    });
    if (blocks.length === 0 && text) return [{ type: 'markdown', content: text }];
    return blocks;
  }
  const blocks: ResponseBlock[] = text ? [{ type: 'markdown', content: text }] : [];
  if (isChartSpec(legacyChart)) blocks.push({ type: 'chart', chart: legacyChart });
  return blocks;
}

/**
 * Ping Python backend to test connection
 */
export async function testBackendHealth(endpoint: string): Promise<{ success: boolean; message: string }> {
  try {
    const healthUrl = endpoint.replace(/\/api\/chat\/?$/, '/health');
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3500);

    const res = await fetch(healthUrl, {
      method: 'GET',
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (res.ok) {
      return { success: true, message: `Connected to Python backend at ${endpoint}` };
    }
    return { success: false, message: `Backend responded with HTTP status ${res.status}` };
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : 'Connection refused';
    return { success: false, message: `Could not reach ${endpoint}: ${errorMsg}` };
  }
}

/**
 * Send chat request to the Python backend's /api/chat endpoint.
 * Request/response shapes mirror AgentResponse in agent/chat.py exactly.
 */
export async function sendChatRequest(
  history: Message[],
  config: BackendConfig
): Promise<ChatResponse> {
  const payload = {
    messages: history.map((m) => ({ role: m.role, content: m.content })),
  };

  let response: Response;
  try {
    response = await fetch(config.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : 'Unknown network failure';
    throw new Error(
      `Failed to connect to Python backend at ${config.endpoint}.\n\nError: ${errorMsg}\n\nMake sure the FastAPI server is running.`,
      { cause: err }
    );
  }

  if (!response.ok) {
    throw new Error(`Python server returned status ${response.status}: ${response.statusText}`);
  }

  const json = await response.json();
  return {
    content: json.text ?? '',
    chartSpec: json.chart_spec ?? null,
    blocks: parseResponseBlocks(json.blocks, json.text ?? '', json.chart_spec),
  };
}
