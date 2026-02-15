import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { ChatState, ChatMessage, Conversation } from '@/types/chat';

const initialState: ChatState = {
  currentConversationId: null,
  conversations: [],
  messages: {},
  isStreaming: false,
  isLoading: false,
  error: null,
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setCurrentConversation: (state, action: PayloadAction<string | null>) => {
      state.currentConversationId = action.payload;
    },
    setConversations: (state, action: PayloadAction<Conversation[]>) => {
      state.conversations = action.payload;
    },
    addConversation: (state, action: PayloadAction<Conversation>) => {
      state.conversations.unshift(action.payload);
    },
    setMessages: (state, action: PayloadAction<{ conversationId: string; messages: ChatMessage[] }>) => {
      state.messages[action.payload.conversationId] = action.payload.messages;
    },
    addMessage: (state, action: PayloadAction<{ conversationId: string; message: ChatMessage }>) => {
      const { conversationId, message } = action.payload;
      if (!state.messages[conversationId] || !Array.isArray(state.messages[conversationId])) {
        state.messages[conversationId] = [];
      }
      state.messages[conversationId].push(message);
    },
    updateLastMessage: (state, action: PayloadAction<{ conversationId: string; content: string }>) => {
      const { conversationId, content } = action.payload;
      const messages = state.messages[conversationId];
      if (messages && messages.length > 0) {
        const lastMessage = messages[messages.length - 1];
        if (lastMessage.role === 'assistant') {
          // Immer requires explicit mutation - create new string reference
          lastMessage.content = lastMessage.content + content;
        }
      }
    },
    setStreaming: (state, action: PayloadAction<boolean>) => {
      state.isStreaming = action.payload;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
      state.isLoading = false;
      state.isStreaming = false;
    },
    clearMessages: (state, action: PayloadAction<string>) => {
      delete state.messages[action.payload];
    },
  },
});

export const {
  setCurrentConversation,
  setConversations,
  addConversation,
  setMessages,
  addMessage,
  updateLastMessage,
  setStreaming,
  setLoading,
  setError,
  clearMessages,
} = chatSlice.actions;

export default chatSlice.reducer;
