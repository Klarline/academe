'use client';

import React, { useEffect } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import MessageList from '@/components/chat/MessageList';
import ChatInput from '@/components/chat/ChatInput';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { useWebSocketChat } from '@/hooks/useWebSocketChat';
// import { useHttpChat } from '@/hooks/useHttpChat';
import { useGetMessagesQuery } from '@/store/api/chatApi';
import { setMessages } from '@/store/slices/chatSlice';
import { WifiOff, Wifi } from 'lucide-react';

export default function ChatPage() {
  const dispatch = useAppDispatch();
  const { currentConversationId, messages, isStreaming } = useAppSelector(state => state.chat);
  const conversationMessages = messages[currentConversationId || 'new'] || [];
  
  // Fetch messages for current conversation
  const { data: fetchedMessages } = useGetMessagesQuery(currentConversationId!, {
    skip: !currentConversationId
  });

  // Load messages into Redux when fetched
  useEffect(() => {
    if (fetchedMessages && currentConversationId) {
      // API returns {messages: [...], total, offset, limit}
      const messageList = Array.isArray(fetchedMessages) 
        ? fetchedMessages 
        : (fetchedMessages?.messages || []);
      
      dispatch(setMessages({
        conversationId: currentConversationId,
        messages: messageList
      }));
    } else if (currentConversationId === null) {
      // Clear messages for new chat
      dispatch(setMessages({
        conversationId: 'new',
        messages: []
      }));
    }
  }, [fetchedMessages, currentConversationId, dispatch]);
  
  const { sendMessage, isConnected, error } = useWebSocketChat(currentConversationId || undefined);
  // const { sendMessage, isLoading, isConnected, error } = useHttpChat(currentConversationId || undefined);

  const handleSendMessage = (content: string) => {
    sendMessage(content);
  };

  return (
    <MainLayout>
      <div className="h-full flex flex-col bg-[#F8F9FA] rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        {/* Connection Status Banner */}
        {!isConnected && (
          <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-2 flex items-center gap-2">
            <WifiOff size={16} className="text-yellow-600" />
            <span className="text-sm text-yellow-800 font-medium">
              {error || 'Connecting to server...'}
            </span>
          </div>
        )}

        {isConnected && (
          <div className="bg-emerald-50 border-b border-emerald-200 px-4 py-2 flex items-center gap-2">
            <Wifi size={16} className="text-emerald-600" />
            <span className="text-sm text-emerald-800 font-medium">Connected</span>
          </div>
        )}

        <MessageList messages={conversationMessages} isLoading={isStreaming} />
        <ChatInput 
          onSend={handleSendMessage} 
          disabled={!isConnected || isStreaming} 
          placeholder={isConnected ? "Ask anything about your learning materials..." : "Connecting to server..."}
        />
      </div>
    </MainLayout>
  );
}
