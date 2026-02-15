import React, { useRef, useEffect } from 'react';
import { ChatMessage as ChatMessageType } from '@/types/chat';
import ChatMessage from './ChatMessage';

interface MessageListProps {
  messages: ChatMessageType[];
  isLoading?: boolean;
}

export default function MessageList({ messages, isLoading }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Ensure messages is always an array
  const messageList = Array.isArray(messages) ? messages : [];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Scroll on messages change OR when last message content changes (streaming)
  useEffect(() => {
    scrollToBottom();
  }, [messageList, messageList[messageList.length - 1]?.content]);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {messageList.length === 0 ? (
        <div className="flex items-center justify-center h-full">
          <div className="text-center max-w-md">
            <h3 className="text-xl font-bold text-slate-800 mb-2">
              Start a conversation
            </h3>
            <p className="text-slate-600">
              Ask me anything about your learning materials. I&apos;ll route your question to the best specialized agent.
            </p>
          </div>
        </div>
      ) : (
        <>
          {messageList.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          
          {isLoading && (
            <div className="flex gap-3">
              <div className="w-10 h-10 rounded-lg bg-slate-200 animate-pulse" />
              <div className="flex-1">
                <div className="h-4 bg-slate-200 rounded w-32 mb-2 animate-pulse" />
                <div className="h-16 bg-slate-100 rounded-2xl animate-pulse" />
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </>
      )}
    </div>
  );
}
