import { useState, useRef, useEffect } from 'react';
import { AlignJustify } from 'lucide-react';
import type { Session, Message, BackendConfig, OutlineItem } from './types';
import { Sidebar } from './components/Sidebar';
import { OutlinePanel } from './components/OutlinePanel';
import { UserMessage } from './components/UserMessage';
import { AssistantMessage } from './components/AssistantMessage';
import { InputDock } from './components/InputDock';
import { PromptPresetsModal } from './components/PromptPresetsModal';
import { DEFAULT_BACKEND_CONFIG, sendChatRequest } from './services/llmClient';

const createEmptySession = (runNumber: number): Session => {
  const sessionCode = `#${Math.floor(100 + Math.random() * 900)}-CHAT`;

  return {
    id: `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    title: `CHAT_${String(runNumber).padStart(2, '0')}`,
    sessionCode,
    bannerTitle: 'CHAT SESSION',
    bannerSubtitle: 'Send a prompt to begin your market analysis.',
    createdAt: new Date().toISOString(),
    outline: [],
    messages: [],
  };
};

export default function App() {
  const [sessions, setSessions] = useState<Session[]>(() => [createEmptySession(1)]);

  const [activeSessionId, setActiveSessionId] = useState<string>(() => sessions[0].id);
  const [backendConfig] = useState<BackendConfig>(() => {
    const saved = localStorage.getItem('arcade_ai_config');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return DEFAULT_BACKEND_CONFIG;
      }
    }
    return DEFAULT_BACKEND_CONFIG;
  });

  const [outlineOpen, setOutlineOpen] = useState<boolean>(true);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 768;
    }
    return true;
  });
  const [isPresetsOpen, setIsPresetsOpen] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Remove chat history saved by earlier versions; sessions are now temporary.
  useEffect(() => {
    try {
      localStorage.removeItem('arcade_ai_sessions');
    } catch {
      // Ignore unavailable browser storage.
    }
  }, []);

  // Active session helper
  const activeSession = sessions.find((session) => session.id === activeSessionId) ?? sessions[0];

  // Scroll to bottom
  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    scrollToBottom('auto');
  }, [activeSessionId]);

  useEffect(() => {
    const closeCompetingPanelOnSmallViewport = () => {
      if (window.innerWidth < 768 && sidebarOpen) setOutlineOpen(false);
    };

    window.addEventListener('resize', closeCompetingPanelOnSmallViewport);
    closeCompetingPanelOnSmallViewport();
    return () => window.removeEventListener('resize', closeCompetingPanelOnSmallViewport);
  }, [sidebarOpen]);

  const handleNewGame = () => {
    const newSession = createEmptySession(sessions.length + 1);
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
  };

  const handleDeleteSession = (id: string) => {
    const remainingSessions = sessions.filter((session) => session.id !== id);
    if (remainingSessions.length === 0) {
      const emptySession = createEmptySession(1);
      setSessions([emptySession]);
      setActiveSessionId(emptySession.id);
      return;
    }

    setSessions(remainingSessions);
    if (activeSessionId === id) setActiveSessionId(remainingSessions[0].id);
  };

  const handleSendMessage = async (
    text: string,
    attachment?: { name: string; size: string }
  ) => {
    if (!text.trim() && !attachment) return;

    const timeStr = new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });

    const userMessage: Message = {
      id: `msg-u-${Date.now()}`,
      role: 'user',
      timestamp: timeStr,
      senderTitle: `USER`,
      content: attachment
        ? `${text}\n[Attached File: ${attachment.name} (${attachment.size})]`
        : text,
      status: 'idle',
    };

    // Update active session with user message
    const updatedMessages = [...activeSession.messages, userMessage];

    // Also update outline if it's a new heading topic
    const newOutline = [...activeSession.outline];
    if (newOutline.length < 6) {
      newOutline.push({
        id: `topic-${Date.now()}`,
        title: text.slice(0, 24) + (text.length > 24 ? '...' : ''),
        messageId: userMessage.id,
      });
    }

    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSessionId
          ? { ...s, messages: updatedMessages, outline: newOutline }
          : s
      )
    );

    setIsLoading(true);
    setTimeout(() => scrollToBottom('smooth'), 50);

    try {
      const response = await sendChatRequest(updatedMessages, backendConfig);

      const botMessage: Message = {
        id: `msg-b-${Date.now()}`,
        role: 'assistant',
        timestamp: new Date().toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        }),
        senderTitle: 'PIXELBOT 64 // MARKET AI',
        content: response.content,
        chartSpec: response.chartSpec,
        contentBlocks: response.blocks,
        status: 'idle',
      };

      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId
            ? { ...s, messages: [...updatedMessages, botMessage] }
            : s
        )
      );
    } catch (err: unknown) {
      const errorMsg =
        err instanceof Error ? err.message : 'Unknown communication error';
      const errorMessage: Message = {
        id: `msg-err-${Date.now()}`,
        role: 'assistant',
        timestamp: new Date().toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        }),
        senderTitle: 'PIXELBOT 64 // SYSTEM ERROR',
        content: `ALERT // BACKEND OFFLINE OR UNREACHABLE:\n\n${errorMsg}\n\nTIP: Check that the FastAPI server is running and reachable.`,
        status: 'error',
      };

      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId
            ? { ...s, messages: [...updatedMessages, errorMessage] }
            : s
        )
      );
    } finally {
      setIsLoading(false);
      setTimeout(() => scrollToBottom('smooth'), 100);
    }
  };

  const handleOutlineClick = (item: OutlineItem) => {
    if (item.messageId) {
      const el = document.getElementById(item.messageId);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('ring-4', 'ring-[#FFD200]');
        setTimeout(() => {
          el.classList.remove('ring-4', 'ring-[#FFD200]');
        }, 1500);
        return;
      }
    }
    // If not matching specific message, jump to top banner or first relevant message
    chatContainerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#EEF2F6]">
      {/* Left Sidebar: Runs & New Game */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={setActiveSessionId}
        onNewGame={handleNewGame}
        onDeleteSession={handleDeleteSession}
        isOpen={sidebarOpen}
        onToggleSidebar={() => {
          const nextOpen = !sidebarOpen;
          if (nextOpen && window.innerWidth < 768) setOutlineOpen(false);
          setSidebarOpen(nextOpen);
        }}
        onCloseMobile={() => setSidebarOpen(false)}
      />

      {/* Center Panel: Chat conversation stream & bottom dock - extends to top of viewport */}
      <main className="flex-1 flex flex-col h-full overflow-hidden bg-[#EEF2F6] relative">
        {/* Floating Utilities (Outline restore if collapsed) */}
        {!outlineOpen && (
          <div className="absolute top-3 right-4 z-10">
            <button
              onClick={() => {
                if (window.innerWidth < 768) setSidebarOpen(false);
                setOutlineOpen(true);
              }}
              title="Show Outline"
              className="flex items-center gap-1.5 h-8 px-2.5 bg-white hover:bg-[#FFD200] border-2 border-black font-arcade-mono text-xs font-bold uppercase retro-shadow-sm cursor-pointer"
            >
              <AlignJustify className="w-3.5 h-3.5" />
              <span>OUTLINE</span>
            </button>
          </div>
        )}

        {/* Sidebar restore button (when collapsed) */}
        {!sidebarOpen && (
          <div className="absolute top-3 left-3 sm:left-4 z-10">
            <button
              onClick={() => {
                if (window.innerWidth < 768) setOutlineOpen(false);
                setSidebarOpen(true);
              }}
              title="Show Sidebar"
              className="flex items-center gap-1.5 h-8 px-2.5 bg-white hover:bg-[#FFD200] border-2 border-black font-arcade-mono text-xs font-bold uppercase retro-shadow-sm cursor-pointer"
            >
              <AlignJustify className="w-3.5 h-3.5 text-black" />
              <span>CHATS</span>
            </button>
          </div>
        )}

        {/* Scrollable messages area extending continuously to bottom of viewport */}
        <div
          ref={chatContainerRef}
          className="flex-1 overflow-y-auto px-2 sm:px-6 pt-10 md:pt-10 pb-28 md:pb-32"
        >

            {/* Messages list */}
            {activeSession.messages.map((message) =>
              message.role === 'user' ? (
                <UserMessage key={message.id} message={message} />
              ) : (
                <AssistantMessage key={message.id} message={message} />
              )
            )}

            {/* Loading indicator while awaiting the backend response */}
            {isLoading && (
              <AssistantMessage
                message={{
                  id: 'loading-preview',
                  role: 'assistant',
                  timestamp: 'NOW',
                  senderTitle: 'PIXELBOT 64 // MARKET AI',
                  content: 'Thinking\u2026',
                  status: 'streaming',
                }}
              />
            )}

            {/* Empty state if new empty run */}
            {activeSession.messages.length === 0 && !isLoading && (
              <div className="my-12 text-center p-8 bg-white border-2 border-black max-w-xl mx-auto retro-shadow">
                <div className="font-arcade text-lg font-bold text-black uppercase mb-2">
                  AWAITING INPUT COMMAND
                </div>
                <p className="font-arcade-body text-xs sm:text-sm text-slate-600 mb-4">
                  Send a query below or select a tactical preset.
                </p>
                <button
                  onClick={() => setIsPresetsOpen(true)}
                  className="px-4 py-2 bg-[#FFD200] hover:bg-yellow-400 font-arcade-mono font-bold text-xs uppercase border-2 border-black retro-shadow-sm retro-button cursor-pointer"
                >
                  View Prompt Presets
                </button>
              </div>
            )}

            <div ref={messagesEndRef} className="h-4" />
        </div>

        {/* Floating Input Dock Area - doesn't cut page scrolling */}
        <div className="absolute bottom-0 inset-x-0 pointer-events-none bg-gradient-to-t from-[#EEF2F6] via-[#EEF2F6]/90 to-transparent pt-6">
          <div className="pointer-events-auto">
            <InputDock
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              onOpenPresets={() => setIsPresetsOpen(true)}
            />
          </div>
        </div>
      </main>

      {/* Right Panel: Outline / Table of Contents */}
      <OutlinePanel
        items={activeSession.outline}
        onItemClick={handleOutlineClick}
        isOpen={outlineOpen}
        onToggleOutline={() => setOutlineOpen(false)}
        onCloseMobile={() => setOutlineOpen(false)}
      />

      {/* Prompt Presets Modal */}
      <PromptPresetsModal
        isOpen={isPresetsOpen}
        onClose={() => setIsPresetsOpen(false)}
        onSelectPreset={(p) => handleSendMessage(p)}
      />
    </div>
  );
}
