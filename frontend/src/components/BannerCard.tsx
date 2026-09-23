import React from 'react';
import { BarChart3 } from 'lucide-react';

interface BannerCardProps {
  sessionCode: string;
  title: string;
  subtitle: string;
}

export const BannerCard: React.FC<BannerCardProps> = ({
  sessionCode,
  title,
  subtitle,
}) => {
  return (
    <div className="w-full bg-white border-2 border-black flex flex-col md:flex-row items-stretch retro-shadow mb-6">
      {/* Left content area */}
      <div className="flex-1 p-5 md:p-6 flex flex-col justify-center">
        {/* Session ID Tag */}
        <div className="inline-block self-start mb-2 px-2.5 py-1 bg-[#2B66FF] text-white font-arcade-mono font-bold text-xs tracking-wider border-2 border-black uppercase retro-shadow-sm">
          SESSION ID: {sessionCode}
        </div>
        {/* Main Title */}
        <h1 className="font-arcade text-xl sm:text-2xl md:text-3xl font-bold tracking-tight text-black uppercase leading-tight mb-2">
          {title}
        </h1>
        {/* Subtitle / Description */}
        <p className="font-arcade-body text-xs sm:text-sm text-slate-700 leading-relaxed max-w-2xl">
          {subtitle}
        </p>
      </div>

      {/* Right Graphic Box: Arcade Yellow with Blue Bar Chart */}
      <div className="w-full md:w-32 bg-[#FFD200] border-t-2 md:border-t-0 md:border-l-2 border-black flex items-center justify-center p-6 shrink-0">
        <div className="flex flex-col items-center justify-center gap-1 text-[#2B66FF]">
          <BarChart3 className="w-12 h-12 stroke-[2.5]" />
          <span className="text-[10px] font-arcade-mono font-bold text-black tracking-widest uppercase">
            TELEMETRY
          </span>
        </div>
      </div>
    </div>
  );
};
