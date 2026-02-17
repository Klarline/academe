import { baseApi } from './baseApi';
import { 
  Document,
  UploadDocumentResponse,
  SearchDocumentsRequest,
  SearchDocumentsResponse 
} from '@/types/document';
import { API_ENDPOINTS } from '@/lib/constants';

export const documentApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getDocuments: builder.query<Document[], void>({
      query: () => API_ENDPOINTS.DOCUMENTS.LIST,
      providesTags: ['Document'],
      transformResponse: (response: any) => {
        // Backend returns {documents: [], total, total_size_bytes}
        // Map backend fields to frontend Document type
        const docs = response.documents || [];
        return docs.map((doc: any) => ({
          id: doc.id,
          user_id: doc.user_id,
          filename: doc.filename,
          file_type: doc.file_type,
          file_size: doc.size_bytes,  // Backend: size_bytes, Frontend: file_size
          page_count: doc.page_count,
          upload_status: doc.status === 'ready' ? 'completed' : doc.status,  // Map statuses
          created_at: doc.created_at,
          updated_at: doc.processed_at || doc.created_at  // Use processed_at as updated_at
        }));
      },
    }),
    uploadDocument: builder.mutation<UploadDocumentResponse, FormData>({
      query: (formData) => ({
        url: API_ENDPOINTS.DOCUMENTS.UPLOAD,
        method: 'POST',
        body: formData,
      }),
      invalidatesTags: ['Document'],
    }),
    deleteDocument: builder.mutation<void, string>({
      query: (id) => ({
        url: API_ENDPOINTS.DOCUMENTS.DELETE(id),
        method: 'DELETE',
      }),
      invalidatesTags: ['Document'],
    }),
    searchDocuments: builder.mutation<SearchDocumentsResponse, SearchDocumentsRequest>({
      query: (searchParams) => ({
        url: API_ENDPOINTS.DOCUMENTS.SEARCH,
        method: 'POST',
        body: searchParams,
      }),
    }),
  }),
});

export const {
  useGetDocumentsQuery,
  useUploadDocumentMutation,
  useDeleteDocumentMutation,
  useSearchDocumentsMutation,
} = documentApi;
