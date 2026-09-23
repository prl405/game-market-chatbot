import type { BackendConfig, ChartSpec, Message } from '../types';

export const DEFAULT_BACKEND_CONFIG: BackendConfig = {
  endpoint: 'http://localhost:8000/api/chat',
};

export interface ChatResponse {
  content: string;
  chartSpec: ChartSpec | null;
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
  };
}
