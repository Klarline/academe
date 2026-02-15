import { AgentType } from '@/lib/constants';

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  agent_used?: AgentType;
  route?: string;
  metadata?: MessageMetadata;
  created_at: string;
}

export interface MessageMetadata {
  rag_sources?: string[];
  tokens_used?: number;
  processing_time?: number;
  has_latex?: boolean;
  has_code?: boolean;
  code_language?: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message?: string;
}

export interface SendMessageRequest {
  message: string;
  conversation_id?: string;
}

export interface SendMessageResponse {
  content: string;
  agent_used: AgentType;
  route: string;
  conversation_id: string;
  message_id: string;
  metadata?: MessageMetadata;
}

export interface StreamingMessage {
  type: 'token' | 'metadata' | 'complete';
  content?: string;
  metadata?: MessageMetadata;
  agent_used?: AgentType;
}

export interface ChatState {
  currentConversationId: string | null;
  conversations: Conversation[];
  messages: Record<string, ChatMessage[]>;
  isStreaming: boolean;
  isLoading: boolean;
  error: string | null;
}
