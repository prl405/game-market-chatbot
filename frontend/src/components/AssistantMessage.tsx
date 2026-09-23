import React from 'react';
import { Gamepad2, Copy, Check } from 'lucide-react';
import type { Message } from '../types';
import { RetroChart } from './RetroChart';

interface AssistantMessageProps {
  message: Message;
}

export const AssistantMessage: React.FC<AssistantMessageProps> = ({ message }) => {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      id={message.id}
      className="flex items-start gap-2.5 my-4 max-w-4xl mx-auto w-full px-2 sm:px-4"
    >
      {/* Yellow Gamepad Avatar on the left */}
      <div className="w-8 h-8 sm:w-9 sm:h-9 bg-[#FFD200] border-2 border-black flex items-center justify-center shrink-0 retro-shadow-sm">
        <Gamepad2 className="w-4 h-4 sm:w-5 sm:h-5 text-black stroke-[2.5]" />
      </div>

      {/* Main Message Card */}
      <div className="flex-1 bg-white border-2 border-black p-4 sm:p-5 retro-shadow overflow-hidden">
        {/* Header: PIXELBOT 64 // Title + Timestamp + Copy action */}
        <div className="flex items-center justify-between pb-2 mb-3 border-b-2 border-black">
          <div className="font-arcade-mono font-bold text-xs sm:text-sm text-[#2B66FF] tracking-wider uppercase truncate">
            {message.senderTitle || 'PIXELBOT 64 // MARKET AI'}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span className="font-arcade-mono text-xs text-slate-500 font-medium">
              {message.timestamp}
            </span>
            <button
              onClick={handleCopy}
              title="Copy response"
              className="p-1 hover:bg-slate-100 border border-transparent hover:border-black transition-all cursor-pointer"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-600" />
              ) : (
                <Copy className="w-3.5 h-3.5 text-slate-600" />
              )}
            </button>
          </div>
        </div>

        {/* Text Content */}
        <div className="font-arcade-body text-sm sm:text-base text-slate-900 leading-relaxed space-y-3 font-normal">
          {message.content ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : null}
          {message.status === 'streaming' && (
            <span className="inline-block w-2 h-4 bg-[#2B66FF] animate-pulse ml-1 align-middle" />
          )}
        </div>

        {/* Chart rendered from the agent's chart_spec, if present */}
        {message.chartSpec && <RetroChart data={message.chartSpec} />}
      </div>
    </div>
  );
};
