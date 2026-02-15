import { Network, BookOpen, Code2, FileSearch, Target, LucideIcon } from 'lucide-react';

export const COLORS = {
  bg: '#F8FAFC',
  secondary: '#90AB8B',
  primary: '#5A7863',
  dark: '#3B4953',
  white: '#ffffff'
} as const;

export type AgentType = 'router' | 'concept_explainer' | 'code_helper' | 'research_agent' | 'practice_generator';

export interface AgentConfig {
  id: AgentType;
  name: string;
  displayName: string;
  color: string;
  bgColor: string;
  textColor: string;
  icon: LucideIcon;
  description: string;
}

export const AGENT_CONFIGS: Record<AgentType, AgentConfig> = {
  router: { id: 'router', name: 'router', displayName: 'Router', color: '#9CA3AF', bgColor: '#F3F4F6', textColor: '#374151', icon: Network, description: 'Routes your question to the best agent' },
  concept_explainer: { id: 'concept_explainer', name: 'concept_explainer', displayName: 'Concept Explainer', color: '#5A7863', bgColor: '#5A7863', textColor: '#FFFFFF', icon: BookOpen, description: 'Explains concepts at your preferred level' },
  code_helper: { id: 'code_helper', name: 'code_helper', displayName: 'Code Helper', color: '#3B82F6', bgColor: '#3B82F6', textColor: '#FFFFFF', icon: Code2, description: 'Generates code examples and helps debug' },
  research_agent: { id: 'research_agent', name: 'research_agent', displayName: 'Research Agent', color: '#8B5CF6', bgColor: '#8B5CF6', textColor: '#FFFFFF', icon: FileSearch, description: 'Searches and summarizes research papers' },
  practice_generator: { id: 'practice_generator', name: 'practice_generator', displayName: 'Practice Generator', color: '#F59E0B', bgColor: '#F59E0B', textColor: '#FFFFFF', icon: Target, description: 'Creates practice problems and quizzes' }
} as const;

export enum LearningLevel { BEGINNER = 'beginner', INTERMEDIATE = 'intermediate', ADVANCED = 'advanced' }
export enum LearningGoal { QUICK_REVIEW = 'quick_review', DEEP_LEARNING = 'deep_learning', EXAM_PREP = 'exam_prep', RESEARCH = 'research' }
export enum ExplanationStyle { INTUITIVE = 'intuitive', BALANCED = 'balanced', TECHNICAL = 'technical' }
export enum RAGFallbackPreference { ALWAYS_ASK = 'always_ask', PREFER_GENERAL = 'prefer_general', STRICT_DOCUMENTS = 'strict_documents' }

export const LEARNING_LEVEL_LABELS: Record<LearningLevel, string> = {
  [LearningLevel.BEGINNER]: 'Beginner',
  [LearningLevel.INTERMEDIATE]: 'Intermediate',
  [LearningLevel.ADVANCED]: 'Advanced'
};

export const LEARNING_GOAL_LABELS: Record<LearningGoal, string> = {
  [LearningGoal.QUICK_REVIEW]: 'Quick Review',
  [LearningGoal.DEEP_LEARNING]: 'Deep Learning',
  [LearningGoal.EXAM_PREP]: 'Exam Prep',
  [LearningGoal.RESEARCH]: 'Research'
};

export const EXPLANATION_STYLE_LABELS: Record<ExplanationStyle, string> = {
  [ExplanationStyle.INTUITIVE]: 'Intuitive',
  [ExplanationStyle.BALANCED]: 'Balanced',
  [ExplanationStyle.TECHNICAL]: 'Technical'
};

export const RAG_FALLBACK_LABELS: Record<RAGFallbackPreference, string> = {
  [RAGFallbackPreference.ALWAYS_ASK]: 'Ask me each time',
  [RAGFallbackPreference.PREFER_GENERAL]: 'Use general knowledge',
  [RAGFallbackPreference.STRICT_DOCUMENTS]: 'Only my documents'
};

export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/api/v1/auth/login',
    REGISTER: '/api/v1/auth/register',
    REFRESH: '/api/v1/auth/refresh',
    LOGOUT: '/api/v1/auth/logout',
    VALIDATE: '/api/v1/auth/validate'
  },
  USERS: {
    ME: '/api/v1/users/me',
    UPDATE: '/api/v1/users/me',
    STATS: '/api/v1/users/me/stats',
    COMPLETE_ONBOARDING: '/api/v1/users/me/complete-onboarding'
  },
  CHAT: {
    MESSAGE: '/api/v1/chat/message',
    MESSAGE_STREAM: '/api/v1/chat/message/stream',
    CONVERSATIONS: '/api/v1/chat/conversations',
    CONVERSATION: (id: string) => `/api/v1/chat/conversations/${id}`,
    MESSAGES: (id: string) => `/api/v1/chat/conversations/${id}/messages`
  },
  DOCUMENTS: {
    UPLOAD: '/api/v1/documents/upload',
    LIST: '/api/v1/documents/',
    DELETE: (id: string) => `/api/v1/documents/${id}`,
    SEARCH: '/api/v1/documents/search'
  },
  PROGRESS: {
    GET: '/api/v1/progress/',
    UPDATE: '/api/v1/progress/update'
  }
} as const;
