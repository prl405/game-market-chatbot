import React from 'react';
import type { OutlineItem } from '../types';
import { ChevronRight, AlignJustify } from 'lucide-react';

interface OutlinePanelProps {
  items: OutlineItem[];
  onItemClick: (item: OutlineItem) => void;
  isOpen: boolean;
  onToggleOutline?: () => void;
  onCloseMobile?: () => void;
}

export const OutlinePanel: React.FC<OutlinePanelProps> = ({
  items,
  onItemClick,
  isOpen,
  onToggleOutline,
  onCloseMobile,
}) => {
  if (!isOpen) return null;

  return (
    <>
      <div
        onClick={onCloseMobile || onToggleOutline}
        className="fixed inset-0 bg-black/40 z-30 md:hidden"
      />
      <aside className="fixed md:static inset-y-0 right-0 z-40 md:z-auto w-56 bg-[#F8FAFC] border-l-2 border-black flex flex-col shrink-0 h-full select-none overflow-hidden">
      {/* Outline header at top of panel */}
      <div className="h-14 border-b-2 border-black flex items-center justify-between px-4 bg-white shrink-0">
        {onToggleOutline && (
          <button
            onClick={() => {
              onToggleOutline();
            }}
            title="Collapse Outline"
            className="p-1 hover:bg-slate-100 border border-black cursor-pointer"
          >
            <AlignJustify className="w-4 h-4 text-black" />
          </button>
        )}
        <span className="font-arcade font-bold text-sm text-black tracking-widest uppercase">
          OUTLINE
        </span>
      </div>

      {/* Outline entries */}
      <div className="p-3 flex flex-col gap-2 overflow-y-auto flex-1">
        <div className="text-[11px] font-arcade-mono font-bold text-slate-500 uppercase px-1 pb-1 border-b border-black">
          INDEX & SECTIONS
        </div>

        {items.map((item) => (
          <button
            key={item.id}
            onClick={() => onItemClick(item)}
            className="w-full text-left p-2 border-2 border-black bg-white hover:bg-[#FFD200] font-arcade-mono text-xs font-bold text-black uppercase transition-colors retro-shadow-sm retro-shadow-active retro-button flex items-center justify-between group cursor-pointer"
          >
            <span className="truncate">{item.title}</span>
            <ChevronRight className="w-3.5 h-3.5 opacity-40 group-hover:opacity-100 shrink-0" />
          </button>
        ))}

        {items.length === 0 && (
          <div className="text-xs font-arcade-mono text-slate-400 p-2 italic">
            No sections detected yet.
          </div>
        )}
      </div>

      <div className="mt-auto p-3 border-t border-black bg-slate-100 text-[10px] font-arcade-mono text-slate-500">
        Click any section to jump directly to that telemetry stream.
      </div>
      </aside>
    </>
  );
};
