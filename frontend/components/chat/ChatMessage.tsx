import React from 'react';
import { ChatMessage as ChatMessageType } from '@/types/chat';
import AgentBadge from './AgentBadge';
import MessageContent from './renderers/MessageContent';
import { formatMessageTime } from '@/lib/utils';
import { User } from 'lucide-react';

interface ChatMessageProps {
  message: ChatMessageType;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  
  // Backend uses 'timestamp', frontend uses 'created_at'
  const messageTime = message.created_at || (message as any).timestamp || new Date().toISOString();

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar/Badge */}
      {isUser ? (
        <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center shrink-0">
          <User size={20} className="text-slate-600" />
        </div>
      ) : (
        message.agent_used && <AgentBadge agentType={message.agent_used} showLabel={false} />
      )}

      {/* Message Content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        {/* Header with agent name and time */}
        {!isUser && message.agent_used && (
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-slate-600 capitalize">
              {message.agent_used.replace('_', ' ')}
            </span>
            <span className="text-xs text-slate-400">{formatMessageTime(messageTime)}</span>
          </div>
        )}

        {/* Message Bubble */}
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-sage-500 text-white'
              : 'bg-white border border-slate-200'
          }`}
        >
          <div className={`leading-relaxed ${isUser ? 'text-white [&_*]:text-white font-medium' : 'text-slate-800 font-medium'}`}>
            <MessageContent content={message.content} />
          </div>
        </div>

        {/* User timestamp */}
        {isUser && (
          <span className="text-xs text-slate-400 mt-1">
            {formatMessageTime(messageTime)}
          </span>
        )}
      </div>
    </div>
  );
}
