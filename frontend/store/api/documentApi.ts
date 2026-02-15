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
