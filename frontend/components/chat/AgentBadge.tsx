import React from 'react';
import { AgentType, AGENT_CONFIGS } from '@/lib/constants';

interface AgentBadgeProps {
  agentType: AgentType;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export default function AgentBadge({ 
  agentType, 
  size = 'md',
  showLabel = true 
}: AgentBadgeProps) {
  const agent = AGENT_CONFIGS[agentType];
  const Icon = agent.icon;
  
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12'
  };
  
  const iconSizes = {
    sm: 16,
    md: 20,
    lg: 24
  };

  return (
    <div className="flex items-center gap-2">
      <div 
        className={`${sizeClasses[size]} rounded-lg flex items-center justify-center shrink-0`}
        style={{ backgroundColor: agent.bgColor }}
      >
        <Icon size={iconSizes[size]} style={{ color: agent.textColor }} />
      </div>
      {showLabel && (
        <span className="text-xs font-medium text-slate-600">
          {agent.displayName}
        </span>
      )}
    </div>
  );
}
