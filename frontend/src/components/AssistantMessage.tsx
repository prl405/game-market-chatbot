import React from 'react';
import { Gamepad2, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../types';
import { RetroChart } from './RetroChart';

interface AssistantMessageProps {
  message: Message;
}

export const AssistantMessage: React.FC<AssistantMessageProps> = ({ message }) => {
  const [copied, setCopied] = React.useState(false);
  const blocks = message.contentBlocks ?? [
    ...(message.content ? [{ type: 'markdown' as const, content: message.content }] : []),
    ...(message.chartSpec ? [{ type: 'chart' as const, chart: message.chartSpec }] : []),
  ];

  const handleCopy = () => {
    const text = blocks.map((block) => block.type === 'markdown'
      ? block.content
      : `[Chart: ${block.chart.title}]\n${block.chart.data
        .map((row) => block.chart.chart_type === 'histogram' && block.chart.x_end_field
          ? `${String(row[block.chart.x_field])} to ${String(row[block.chart.x_end_field])}: ${String(row[block.chart.y_field])}`
          : `${String(row[block.chart.x_field])}: ${String(row[block.chart.y_field])}`)
        .join('\n')}`).join('\n\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      id={message.id}
      className="flex items-start gap-2.5 my-4 max-w-4xl mx-auto w-full px-2 sm:px-4"
    >
      {/* Yellow Gamepad Avatar on the left */}
      <div className="w-8 h-8 sm:w-9 sm:h-9 bg-[#2B66FF] border-2 border-black flex items-center justify-center shrink-0 retro-shadow-sm">
        <Gamepad2 className="w-4 h-4 sm:w-5 sm:h-5 text-white stroke-[2.5]" />
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
              className="p-1 hover:bg-slate-100 border border-transparent hover:border-black transition-all retro-shadow-sm retro-button cursor-pointer"
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
        <div className="font-arcade-body text-sm sm:text-base text-slate-900 leading-relaxed space-y-4 font-normal break-words">
          {blocks.map((block, index) => block.type === 'markdown' ? (
            <div key={`markdown-${index}`} className="space-y-3 [&_h1]:font-bold [&_h1]:text-xl [&_h1]:leading-tight [&_h2]:font-bold [&_h2]:text-lg [&_h2]:leading-tight [&_h3]:font-bold [&_h3]:text-base [&_ul]:list-disc [&_ul]:pl-6 [&_ol]:list-decimal [&_ol]:pl-6 [&_li]:pl-1 [&_blockquote]:border-l-4 [&_blockquote]:border-[#2B66FF] [&_blockquote]:pl-3 [&_blockquote]:text-slate-600 [&_a]:text-[#1747B8] [&_a]:underline [&_code]:break-all [&_pre]:max-w-full [&_pre]:overflow-x-auto [&_pre]:border [&_pre]:border-slate-300 [&_pre]:bg-slate-100 [&_pre]:p-3 [&_pre_code]:bg-transparent [&_pre_code]:p-0">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  table: ({ children }) => (
                    <div className="max-w-full overflow-x-auto border border-black">
                      <table className="min-w-full border-collapse text-left text-sm">{children}</table>
                    </div>
                  ),
                  th: ({ children }) => <th className="whitespace-nowrap border border-black bg-[#2B66FF] px-2 py-1.5 font-bold text-white">{children}</th>,
                  td: ({ children }) => <td className="border border-black px-2 py-1.5 align-top">{children}</td>,
                  a: ({ href, children }) => <a href={href} target="_blank" rel="noreferrer">{children}</a>,
                }}
              >
                {block.content}
              </ReactMarkdown>
            </div>
          ) : (
            <RetroChart key={`chart-${index}`} data={block.chart} />
          ))}
          {message.status === 'streaming' && (
            <span className="inline-block w-2 h-4 bg-[#2B66FF] animate-pulse ml-1 align-middle" />
          )}
        </div>

      </div>
    </div>
  );
};
