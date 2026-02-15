import { baseApi } from './baseApi';

export interface PracticeQuestion {
  question: string;
  type: 'mcq' | 'short' | 'code' | 'explain';
  answer: string;
  explanation?: string;
  options?: string[];
}

export interface PracticeSet {
  topic: string;
  difficulty: string;
  questions: PracticeQuestion[];
  sources: string[];
  total_questions: number;
}

export const practiceApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    generatePractice: builder.mutation<PracticeSet, { 
      topic: string; 
      num_questions?: number;
      question_types?: string[];
    }>({
      query: (data) => ({
        url: '/api/v1/practice/generate',
        method: 'POST',
        body: data,
      }),
    }),
    generateQuiz: builder.mutation<PracticeSet, { document_id: string; quiz_length?: number }>({
      query: (data) => ({
        url: '/api/v1/practice/quiz',
        method: 'POST',
        body: data,
      }),
    }),
    
    savePracticeSession: builder.mutation<any, any>({
      query: (session) => ({
        url: '/api/v1/practice/sessions',
        method: 'POST',
        body: session,
      }),
      invalidatesTags: ['PracticeSessions', 'UserStats'],
    }),
    
    getPracticeSessions: builder.query<any[], { topic?: string; skip?: number; limit?: number }>({
      query: ({ topic, skip = 0, limit = 20 }) => ({
        url: '/api/v1/practice/sessions',
        params: { topic, skip, limit },
      }),
      providesTags: ['PracticeSessions'],
    }),
    
    getPracticeSession: builder.query<any, string>({
      query: (sessionId) => `/api/v1/practice/sessions/${sessionId}`,
      providesTags: (result, error, id) => [{ type: 'PracticeSessions', id }],
    }),
    
    deletePracticeSession: builder.mutation<{ message: string }, string>({
      query: (sessionId) => ({
        url: `/api/v1/practice/sessions/${sessionId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['PracticeSessions', 'UserStats'],
    }),
    
    getPracticeStats: builder.query<any, void>({
      query: () => '/api/v1/practice/stats',
      providesTags: ['PracticeStats'],
    }),
  }),
});

export const {
  useGeneratePracticeMutation,
  useGenerateQuizMutation,
  useSavePracticeSessionMutation,
  useGetPracticeSessionsQuery,
  useGetPracticeSessionQuery,
  useDeletePracticeSessionMutation,
  useGetPracticeStatsQuery,
} = practiceApi;
