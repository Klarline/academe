import { baseApi } from './baseApi';
import { 
  Conversation,
  ChatMessage,
  SendMessageRequest,
  SendMessageResponse 
} from '@/types/chat';
import { API_ENDPOINTS } from '@/lib/constants';

export const chatApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getConversations: builder.query<{ conversations: Conversation[]; total: number; page: number; limit: number }, void>({
      query: () => API_ENDPOINTS.CHAT.CONVERSATIONS,
      providesTags: ['Conversation'],
    }),
    getMessages: builder.query<{ messages: ChatMessage[]; total: number; offset: number; limit: number }, string>({
      query: (conversationId) => API_ENDPOINTS.CHAT.MESSAGES(conversationId),
      providesTags: (result, error, conversationId) => [
        { type: 'Message', id: conversationId }
      ],
    }),
    sendMessage: builder.mutation<SendMessageResponse, SendMessageRequest>({
      query: (message) => ({
        url: API_ENDPOINTS.CHAT.MESSAGE,
        method: 'POST',
        body: message,
      }),
      invalidatesTags: ['Conversation', 'Message'],
    }),
  }),
});

export const {
  useGetConversationsQuery,
  useGetMessagesQuery,
  useSendMessageMutation,
} = chatApi;
