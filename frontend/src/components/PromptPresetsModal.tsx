import React from 'react';
import { X, Sparkles, Terminal } from 'lucide-react';

interface PromptPresetsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectPreset: (promptText: string) => void;
}

const PRESETS = [
  {
    category: 'MARKET TELEMETRY',
    title: 'RPG vs FPS Revenue Comparison',
    prompt:
      'Give me the latest revenue breakdown comparing RPG vs FPS global markets, and list the current engine market share for indie developers.',
  },
  {
    category: 'GAMEPLAY MECHANICS',
    title: 'Boss Raid Tactical Intel',
    prompt:
      'What is the optimal DPS rotation against Titan Mech in Phase 2, and what are the hitbox vulnerabilities?',
  },
  {
    category: 'SPEEDRUN & OPTIMIZATION',
    title: 'Ledge-Cancel Frame Windows',
    prompt:
      'How do I optimize the frame input window on Sector 3 ledge-cancels to maintain maximum momentum?',
  },
  {
    category: 'PLOTS & CHARTS',
    title: 'Plot 12-Month Player Retention (Line & Bar)',
    prompt:
      'Plot a line and bar chart showing 12-month player retention comparing 2024 actuals vs 2025 projected telemetry.',
  },
  {
    category: 'ECONOMY & METRICS',
    title: 'Battle Pass Retention Analysis',
    prompt:
      'Analyze the day-30 retention curve differences between paid battle passes and loot-drop progression in live-service titles.',
  },
];

export const PromptPresetsModal: React.FC<PromptPresetsModalProps> = ({
  isOpen,
  onClose,
  onSelectPreset,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs select-none">
      <div className="w-full max-w-lg bg-white border-3 border-black retro-shadow flex flex-col max-h-[85vh] overflow-hidden">
        {/* Header */}
        <div className="bg-[#FFD200] text-black p-3 border-b-2 border-black flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 stroke-[2.5]" />
            <span className="font-arcade-mono font-bold text-xs sm:text-sm tracking-wider uppercase">
              TACTICAL PROMPT PRESETS
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-yellow-400 border border-transparent hover:border-black cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Presets List */}
        <div className="p-4 space-y-3 overflow-y-auto font-arcade-mono">
          {PRESETS.map((p, idx) => (
            <button
              key={idx}
              onClick={() => {
                onSelectPreset(p.prompt);
                onClose();
              }}
              className="w-full text-left p-3 border-2 border-black bg-[#FAFBFD] hover:bg-[#FFD200] group transition-colors retro-shadow-sm retro-shadow-active cursor-pointer"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-[#2B66FF] font-bold group-hover:text-black uppercase tracking-wider">
                  {p.category}
                </span>
                <Terminal className="w-3.5 h-3.5 opacity-40 group-hover:opacity-100" />
              </div>
              <div className="text-xs font-bold text-black uppercase mb-1">
                {p.title}
              </div>
              <div className="text-[11px] text-slate-600 line-clamp-2 font-normal">
                {p.prompt}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
