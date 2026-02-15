import { 
  LearningLevel, 
  LearningGoal, 
  ExplanationStyle, 
  RAGFallbackPreference 
} from '@/lib/constants';

export interface UserProfile {
  id: string;
  email: string;
  username: string;
  learning_level: LearningLevel;
  learning_goal: LearningGoal;
  explanation_style: ExplanationStyle;
  rag_fallback_preference: RAGFallbackPreference;
  preferred_code_language: string;
  include_math_formulas: boolean;
  include_visualizations: boolean;
  has_completed_onboarding: boolean;
  has_seen_rag_explanation: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
}

export interface UserStats {
  total_conversations: number;
  total_messages: number;
  documents_uploaded: number;
  concepts_studied: number;
  study_streak_days: number;
  total_study_time_hours: number;
}

export interface UpdateUserProfileRequest {
  username?: string;
  learning_level?: LearningLevel;
  learning_goal?: LearningGoal;
  explanation_style?: ExplanationStyle;
  rag_fallback_preference?: RAGFallbackPreference;
  preferred_code_language?: string;
  include_math_formulas?: boolean;
  include_visualizations?: boolean;
}

export interface CompleteOnboardingRequest {
  learning_level: LearningLevel;
  learning_goal: LearningGoal;
  explanation_style: ExplanationStyle;
  rag_fallback_preference: RAGFallbackPreference;
  preferred_code_language: string;
  include_math_formulas: boolean;
  include_visualizations: boolean;
}
