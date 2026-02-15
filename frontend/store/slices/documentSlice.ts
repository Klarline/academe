import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { DocumentState, Document } from '@/types/document';

const initialState: DocumentState = {
  documents: [],
  isUploading: false,
  uploadProgress: 0,
  isLoading: false,
  error: null,
};

const documentSlice = createSlice({
  name: 'document',
  initialState,
  reducers: {
    setDocuments: (state, action: PayloadAction<Document[]>) => {
      state.documents = action.payload;
      state.error = null;
    },
    addDocument: (state, action: PayloadAction<Document>) => {
      state.documents.unshift(action.payload);
    },
    removeDocument: (state, action: PayloadAction<string>) => {
      state.documents = state.documents.filter(doc => doc.id !== action.payload);
    },
    setUploading: (state, action: PayloadAction<boolean>) => {
      state.isUploading = action.payload;
      if (!action.payload) {
        state.uploadProgress = 0;
      }
    },
    setUploadProgress: (state, action: PayloadAction<number>) => {
      state.uploadProgress = action.payload;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
      state.isLoading = false;
      state.isUploading = false;
    },
  },
});

export const {
  setDocuments,
  addDocument,
  removeDocument,
  setUploading,
  setUploadProgress,
  setLoading,
  setError,
} = documentSlice.actions;

export default documentSlice.reducer;
