import React, { useRef, useState, useEffect } from 'react';
import { Sparkles, Send } from 'lucide-react';

interface InputDockProps {
  onSendMessage: (text: string, attachment?: { name: string; size: string }) => void;
  isLoading: boolean;
  onOpenPresets?: () => void;
}

export const InputDock: React.FC<InputDockProps> = ({
  onSendMessage,
  isLoading,
  onOpenPresets,
}) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const newHeight = Math.min(textareaRef.current.scrollHeight, 140);
      textareaRef.current.style.height = `${Math.max(44, newHeight)}px`;
    }
  }, [input]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    onSendMessage(trimmed);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-2 sm:px-4 pb-4 pt-2">
      {/* Main input dock row */}
      <div className="flex items-end gap-2">
        {/* Preset / Command Prompts Button */}
        <button
          type="button"
          onClick={() => {
            if (onOpenPresets) onOpenPresets();
          }}
          title="Prompt Presets & Retro Macros"
          className="w-10 h-10 border-2 border-black bg-white hover:bg-[#FFD200] flex items-center justify-center retro-shadow-sm retro-shadow-active retro-button shrink-0 transition-colors cursor-pointer"
        >
          <Sparkles className="w-4 h-4 text-black stroke-[2.5]" />
        </button>

        {/* Text Area Input Box */}
        <div className="flex-1 min-w-0 bg-white border-2 border-black px-3 py-1.5 flex items-center retro-shadow-sm focus-within:ring-2 focus-within:ring-[#2B66FF]">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder="Input prompt or command... (Enter to send, Shift+Enter for newline)"
            className="w-full resize-none bg-transparent font-arcade-mono text-xs sm:text-sm text-black placeholder:text-slate-400 focus:outline-none leading-relaxed max-h-36 py-1"
          />
        </div>

        {/* Send Button: SEND */}
        <button
          type="button"
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
          className={`h-10 px-4 sm:px-5 border-2 border-black font-arcade-mono font-bold text-xs sm:text-sm tracking-wider uppercase flex items-center justify-center gap-1.5 retro-shadow retro-shadow-active retro-button shrink-0 transition-all cursor-pointer ${
            isLoading || !input.trim()
              ? 'bg-slate-200 text-slate-400 border-slate-400 cursor-not-allowed shadow-none'
              : 'bg-[#2B66FF] hover:bg-[#2052D4] text-white active:translate-x-0.5 active:translate-y-0.5'
          }`}
        >
          <span>SEND</span>
          <Send className="w-3.5 h-3.5 stroke-[3]" />
        </button>
      </div>
    </div>
  );
};
