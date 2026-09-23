export type Role = 'user' | 'assistant';

// Mirrors the backend's chart_spec shape exactly — see
// src/game_market_chatbot/tools/chart_spec.py and agent/tool_calls.py.
export interface ChartSpec {
  chart_type: 'bar' | 'line' | 'scatter' | 'pie';
  data: Record<string, unknown>[];
  x_field: string;
  y_field: string;
  title: string;
}

export type ResponseBlock =
  | { type: 'markdown'; content: string }
  | { type: 'chart'; chart: ChartSpec };

export interface Message {
  id: string;
  role: Role;
  content: string;
  timestamp: string;
  senderTitle?: string; // e.g. "PIXELBOT 64 // MARKET AI" or "USER"
  chartSpec?: ChartSpec | null;
  contentBlocks?: ResponseBlock[];
  status?: 'idle' | 'streaming' | 'error';
  sectionAnchorId?: string; // for Outline linking
}

export interface OutlineItem {
  id: string;
  title: string;
  messageId?: string;
  level?: number;
}

export interface Session {
  id: string;
  title: string; // e.g. "CHALLENGE_01.EXE"
  sessionCode: string; // e.g. "#889-MARKET-VAL"
  bannerTitle: string; // e.g. "VIDEO GAME MARKET INTEL // Q3 2024"
  bannerSubtitle: string; // e.g. "Autonomous analysis active..."
  messages: Message[];
  outline: OutlineItem[];
  createdAt: string;
}

export interface BackendConfig {
  endpoint: string; // e.g. "http://localhost:8000/api/chat"
}
