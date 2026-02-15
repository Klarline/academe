import { useEffect, useRef, useState } from 'react';
import { ChatWebSocket } from '@/lib/websocket/ChatWebSocket';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { addMessage, updateLastMessage, setStreaming } from '@/store/slices/chatSlice';
import { ChatMessage } from '@/types/chat';

export function useWebSocketChat(conversationId?: string) {
  const wsRef = useRef<ChatWebSocket | null>(null);
  const { accessToken } = useAppSelector(state => state.auth);
  const dispatch = useAppDispatch();
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    if (!accessToken) {
      setError('Not authenticated');
      return;
    }

    const ws = new ChatWebSocket(accessToken);
    wsRef.current = ws;

    ws.onOpen(() => {
      if (mountedRef.current) {
        setIsConnected(true);
        setError(null);
      }
    });

    ws.onMessage((data) => {
      if (!mountedRef.current) return;

      if (data.type === 'token' || data.type === 'stream_chunk') {
        dispatch(updateLastMessage({
          conversationId: conversationId || 'new',
          content: data.content || data.chunk || ''
        }));
      } else if (data.type === 'complete' || data.type === 'end_streaming') {
        dispatch(setStreaming(false));
      }
    });

    ws.onError((error) => {
      if (mountedRef.current) {
        setError('Connection error');
        setIsConnected(false);
      }
    });

    ws.onClose(() => {
      if (mountedRef.current) {
        setIsConnected(false);
      }
    });

    ws.connect(conversationId);

    return () => {
      mountedRef.current = false;
      ws.disconnect();
    };
  }, [accessToken, conversationId, dispatch]);

  const sendMessage = (message: string) => {
    if (wsRef.current?.isConnected()) {
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        conversation_id: conversationId || 'new',
        role: 'user',
        content: message,
        created_at: new Date().toISOString(),
      };

      dispatch(addMessage({
        conversationId: conversationId || 'new',
        message: userMessage
      }));

      // Add empty assistant message for streaming
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        conversation_id: conversationId || 'new',
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      };

      dispatch(addMessage({
        conversationId: conversationId || 'new',
        message: assistantMessage
      }));

      dispatch(setStreaming(true));
      wsRef.current.sendMessage(message, conversationId);
    } else {
      setError('Not connected to server');
    }
  };

  return { sendMessage, isConnected, error };
}
