export interface Document {
  id: string;
  user_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  content_preview?: string;
  page_count?: number;
  upload_status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
}

export interface UploadDocumentRequest {
  file: File;
}

export interface UploadDocumentResponse {
  document_id: string;
  filename: string;
  status: string;
  message: string;
}

export interface SearchDocumentsRequest {
  query: string;
  top_k?: number;
}

export interface SearchResult {
  document_id: string;
  filename: string;
  chunk_text: string;
  similarity_score: number;
  page_number?: number;
}

export interface SearchDocumentsResponse {
  results: SearchResult[];
  query: string;
}

export interface DocumentState {
  documents: Document[];
  isUploading: boolean;
  uploadProgress: number;
  isLoading: boolean;
  error: string | null;
}
