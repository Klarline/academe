import { useState } from 'react';
import { useAppDispatch } from '@/store/hooks';
import { addMessage, updateLastMessage, setStreaming } from '@/store/slices/chatSlice';
import { useSendMessageMutation } from '@/store/api/chatApi';
import { ChatMessage } from '@/types/chat';
import toast from 'react-hot-toast';

export function useHttpChat(conversationId?: string) {
  const dispatch = useAppDispatch();
  const [sendMessageApi, { isLoading }] = useSendMessageMutation();
  const [error, setError] = useState<string | null>(null);

  const sendMessage = async (content: string) => {
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      conversation_id: conversationId || 'new',
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    dispatch(addMessage({
      conversationId: conversationId || 'new',
      message: userMessage
    }));

    // Add empty assistant message for "streaming" effect
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

    try {
      const result = await sendMessageApi({
        message: content,
        conversation_id: conversationId
      }).unwrap();

      // Simulate streaming by revealing text character by character
      const fullText = result.content;
      
      if (!fullText) {
        console.error('No content in response:', result);
        dispatch(setStreaming(false));
        toast.error('Received empty response');
        return;
      }

      const chunkSize = 3; // Characters per chunk
      const delay = 10; // ms between chunks

      for (let i = 0; i < fullText.length; i += chunkSize) {
        const chunk = fullText.slice(i, i + chunkSize);
        dispatch(updateLastMessage({
          conversationId: result.conversation_id,
          content: chunk
        }));
        await new Promise(resolve => setTimeout(resolve, delay));
      }

      dispatch(setStreaming(false));
      
    } catch (err: any) {
      setError(err?.data?.detail || 'Failed to send message');
      dispatch(setStreaming(false));
      toast.error('Failed to send message');
    }
  };

  return {
    sendMessage,
    isLoading,
    error,
    isConnected: true,
  };
}
