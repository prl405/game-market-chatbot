import React from 'react';
import { Plus, History, Trash2, Gamepad2, AlignJustify } from 'lucide-react';
import type { Session } from '../types';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string;
  onSelectSession: (id: string) => void;
  onNewGame: () => void;
  onDeleteSession: (id: string) => void;
  isOpen: boolean;
  onToggleSidebar?: () => void;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewGame,
  onDeleteSession,
  isOpen,
  onToggleSidebar,
  onCloseMobile,
}) => {
  if (!isOpen) return null;

  return (
    <>
      {/* Mobile backdrop */}
      <div
        onClick={onCloseMobile || onToggleSidebar}
        className="fixed inset-0 bg-black/40 z-30 md:hidden"
      />

      <aside className="fixed md:static inset-y-0 left-0 z-40 w-64 bg-[#F8FAFC] border-r-2 border-black flex flex-col justify-between shrink-0 h-full select-none overflow-hidden">
        {/* Brand header at top of sidebar */}
        <div className="h-14 border-b-2 border-black flex items-center justify-between px-4 bg-white shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="font-arcade text-l font-bold tracking-wider text-[#2B66FF] uppercase">
              GameGauge AI
            </span>
            <div className="w-7 h-7 bg-[#FFD200] border-2 border-black flex items-center justify-center retro-shadow-sm">
              <Gamepad2 className="w-4 h-4 text-black stroke-[2.5]" />
            </div>
          </div>
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              title="Collapse Sidebar"
              className="p-1 hover:bg-slate-100 border border-black cursor-pointer"
            >
              <AlignJustify className="w-4 h-4 text-black" />
            </button>
          )}
        </div>

        {/* Top section: New Game + Session List */}
        <div className="p-3 flex flex-col gap-3 overflow-y-auto flex-1">
          {/* + NEW GAME Button */}
          <button
            onClick={onNewGame}
            className="w-full py-2.5 px-3 bg-[#2B66FF] hover:bg-[#2052D4] text-white font-arcade-mono font-bold text-sm tracking-wider uppercase border-2 border-black retro-shadow retro-shadow-active retro-button flex items-center justify-center gap-2 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4 stroke-[3]" />
            <span>NEW CHAT</span>
          </button>

          {/* Session runs list */}
          <div className="flex flex-col gap-2 pt-2">
            <span className="text-[11px] font-arcade-mono font-bold text-slate-500 uppercase px-1">
              CURRENT CHATS
            </span>
            {sessions.map((session) => {
              const isActive = session.id === activeSessionId;
              return (
                <div
                  key={session.id}
                  className="group relative flex items-center"
                >
                  <button
                    onClick={() => onSelectSession(session.id)}
                    className={`w-full text-left py-2.5 px-3 border-2 border-black font-arcade-mono font-bold text-xs uppercase flex items-center gap-2 transition-all retro-button cursor-pointer ${
                      isActive
                        ? 'bg-[#FFD200] text-black retro-shadow'
                        : 'bg-white text-black hover:bg-slate-100 hover:border-black retro-shadow-sm'
                    }`}
                  >
                    <History className="w-4 h-4 shrink-0 stroke-[2.5]" />
                    <span className="truncate flex-1">
                      {session.title.replace(/\.EXE$/i, '').replaceAll('_', ' ')}
                    </span>
                  </button>
                  {/* Delete button (if more than 1 session) */}
                  {sessions.length > 1 && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(session.id);
                      }}
                      title="Delete Run"
                      className="absolute right-2 opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 border border-transparent hover:border-black transition-opacity retro-button retro-shadow-sm"
                    >
                      <Trash2 className="w-3.5 h-3.5 text-red-600" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Bottom Description Box */}
        <div className="mt-auto p-3 border-t border-black bg-slate-100 text-[10px] font-arcade-mono text-slate-500">
          Chats stay available until you restart the app.
        </div>
      </aside>
    </>
  );
};
