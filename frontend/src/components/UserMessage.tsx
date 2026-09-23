import React from 'react';
import { User } from 'lucide-react';
import type { Message } from '../types';

interface UserMessageProps {
  message: Message;
}

export const UserMessage: React.FC<UserMessageProps> = ({ message }) => {
  return (
    <div
      id={message.id}
      className="flex justify-end items-start gap-2.5 my-4 max-w-4xl mx-auto w-full px-2 sm:px-4"
    >
      {/* Blue message container */}
      <div className="flex-1 max-w-2xl bg-[#FFD200] border-2 border-black p-4 text-white retro-shadow">
        {/* Header: USER // Timestamp */}
        <div className="flex items-center justify-between font-arcade-mono font-bold text-s text-black tracking-wider mb-1.5 uppercase border-b-2 border-black pb-1.5">
          <span>{message.senderTitle}</span>
          <span className="font-arcade-mono text-xs text-slate-500 font-medium">{message.timestamp}</span>
        </div>
        {/* Message body */}
        <p className="font-arcade-body text-sm sm:text-base leading-relaxed text-black font-medium whitespace-pre-wrap">
          {message.content}
        </p>
      </div>
      {/* User avatar on the right */}
      <div className="w-8 h-8 sm:w-9 sm:h-9 bg-[#FFD200] border-2 border-black flex items-center justify-center shrink-0 retro-shadow-sm text-white">
        {/* User avatar icon black on yellow background */}
        <User className="w-4 h-4 sm:w-5 sm:h-5 text-black stroke-[2.5]" />
      </div>
    </div>
  );
};
