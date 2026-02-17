import { baseApi } from './baseApi';
import { API_ENDPOINTS } from '@/lib/constants';

export interface ResearchRequest {
  query: string;
  conversation_id?: string;
  top_k?: number;
  use_citations?: boolean;
}

export interface SourceInfo {
  document_id: string;
  filename: string;
  page_number: number | null;
  section_title: string | null;
  relevance_score: number;
  excerpt: string;
}

export interface ResearchResponse {
  answer: string;
  sources: SourceInfo[];
  agent_used: string;
  processing_time_ms: number | null;
  conversation_id: string | null;
}

export const researchApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    askResearchQuestion: builder.mutation<ResearchResponse, ResearchRequest>({
      query: (request) => ({
        url: API_ENDPOINTS.RESEARCH.QUERY,
        method: 'POST',
        body: request,
      }),
    }),
    summarizeDocument: builder.mutation<{ document_id: string; summary: string }, string>({
      query: (documentId) => ({
        url: API_ENDPOINTS.RESEARCH.SUMMARIZE(documentId),
        method: 'POST',
      }),
    }),
  }),
});

export const {
  useAskResearchQuestionMutation,
  useSummarizeDocumentMutation,
} = researchApi;
