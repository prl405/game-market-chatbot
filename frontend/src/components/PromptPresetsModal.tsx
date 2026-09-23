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
    title: 'Top 10 Games by Copies Sold',
    prompt: 'What are the top 10 games by copies sold?',
  },
  {
    category: 'GENRE ANALYSIS',
    title: 'Genre Share of Copies Sold',
    prompt: 'What percentage share of total copies sold does each genre represent?',
  },
  {
    category: 'PRICING',
    title: 'Games Priced at $9.99 or Below',
    prompt: 'How many games are priced at $9.99 or below?',
  },
  {
    category: 'PRICING',
    title: 'Median Game Price',
    prompt: 'What is the median price of games in the dataset?',
  },
  {
    category: 'RELEASES',
    title: 'Games Released in 2024',
    prompt: 'How many games were released in 2024?',
  },
  {
    category: 'REVIEWS',
    title: 'Review Score Distribution',
    prompt:
      'Give me the distribution of game review-scores on Steam.',
  },
  {
    category: 'PUBLISHERS',
    title: 'Top 10 Publishers by Game Count',
    prompt: 'Which publishers have released the most games? Select the top 10 publishers.',
  },
  {
    category: 'GENRE ANALYSIS',
    title: 'Top 10 RPG Games by Copies Sold',
    prompt: 'What are the top games in the RPG genre by copies sold? Select the top 10 games.',
  },
  {
    category: 'MARKET COMPARISON',
    title: 'Comparable Indie RPGs',
    prompt:
      'How many games are comparable to a $10-30 Indie RPG released between 2020 and 2024?',
  },
  {
    category: 'SALES ANALYSIS',
    title: '95th-Percentile Sales Outliers',
    prompt:
      'Which games are 95th-percentile outlier successes by copies sold? Select the top 10 games.',
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
