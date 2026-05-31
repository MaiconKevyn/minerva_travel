
import React from 'react';
import { cn } from '@/lib/utils';

const WarmCard = ({ children, className, ...props }) => {
  return (
    <div 
      className={cn(
        "bg-card rounded-3xl p-6 md:p-8 storybook-shadow border border-border/50 relative overflow-hidden",
        className
      )}
      {...props}
    >
      {/* Subtle top inner glow for a warm, soft feel */}
      <div className="absolute top-0 left-0 right-0 h-2 bg-gradient-to-b from-white/60 to-transparent pointer-events-none" />
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
};

export default WarmCard;
