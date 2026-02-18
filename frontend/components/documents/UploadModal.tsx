'use client';

import React, { useState, useCallback } from 'react';
import { X, Upload, File, CheckCircle, AlertCircle } from 'lucide-react';
import { COLORS } from '@/lib/constants';
import { useUploadDocumentMutation } from '@/store/api/documentApi';
import toast from 'react-hot-toast';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function UploadModal({ isOpen, onClose }: UploadModalProps) {
  const [uploadDocument, { isLoading }] = useUploadDocumentMutation();
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');

  const acceptedTypes = ['.pdf', '.txt', '.md'];
  const maxSize = 10 * 1024 * 1024; // 10MB

  const validateFile = (file: File): string | null => {
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!acceptedTypes.includes(extension)) {
      return `Invalid file type. Please upload ${acceptedTypes.join(', ')} files.`;
    }
    
    if (file.size > maxSize) {
      return 'File too large. Maximum size is 10MB.';
    }
    
    return null;
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files[0]) {
      const error = validateFile(files[0]);
      if (error) {
        toast.error(error);
      } else {
        setSelectedFile(files[0]);
      }
    }
  }, [validateFile]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files[0]) {
      const error = validateFile(files[0]);
      if (error) {
        toast.error(error);
      } else {
        setSelectedFile(files[0]);
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploadStatus('uploading');
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      // Simulate progress (since we can't track actual upload progress easily)
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      await uploadDocument(formData).unwrap();

      clearInterval(progressInterval);
      setUploadProgress(100);
      setUploadStatus('success');
      
      toast.success('Document uploaded successfully!');
      
      setTimeout(() => {
        onClose();
        setSelectedFile(null);
        setUploadStatus('idle');
        setUploadProgress(0);
      }, 1500);
      
    } catch (error: any) {
      setUploadStatus('error');
      toast.error(error?.data?.detail || 'Upload failed');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <h3 className="text-xl font-bold text-slate-800">Upload Document</h3>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
            <X size={20} className="text-slate-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Drag and Drop Area */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
              dragActive 
                ? 'border-sage-500 bg-sage-50' 
                : 'border-slate-300 hover:border-slate-400'
            }`}
          >
            <div className="flex flex-col items-center gap-4">
              <div 
                className="w-16 h-16 rounded-full flex items-center justify-center"
                style={{ backgroundColor: `${COLORS.secondary}20`, color: COLORS.primary }}
              >
                <Upload size={32} />
              </div>
              
              {selectedFile ? (
                <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                  <File size={20} className="text-slate-600" />
                  <div className="text-left flex-1">
                    <p className="font-medium text-slate-800 text-sm">{selectedFile.name}</p>
                    <p className="text-xs text-slate-500">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                  <button onClick={() => setSelectedFile(null)} className="p-1 hover:bg-slate-200 rounded">
                    <X size={16} className="text-slate-500" />
                  </button>
                </div>
              ) : (
                <>
                  <div>
                    <p className="text-slate-700 font-medium mb-1">
                      Drag and drop your file here
                    </p>
                    <p className="text-sm text-slate-500">
                      or click to browse
                    </p>
                  </div>
                  
                  <input
                    type="file"
                    id="file-upload"
                    className="hidden"
                    accept={acceptedTypes.join(',')}
                    onChange={handleFileSelect}
                  />
                  <label
                    htmlFor="file-upload"
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg cursor-pointer transition-colors font-medium text-sm"
                  >
                    Choose File
                  </label>
                  
                  <p className="text-xs text-slate-400">
                    Supported: PDF, TXT, MD (Max 10MB)
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Upload Progress */}
          {uploadStatus === 'uploading' && (
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-slate-700">Uploading...</span>
                <span className="text-sm text-slate-500">{uploadProgress}%</span>
              </div>
              <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-sage-500 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Success State */}
          {uploadStatus === 'success' && (
            <div className="mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-3">
              <CheckCircle size={20} className="text-emerald-600" />
              <div>
                <p className="font-medium text-emerald-800 text-sm">Upload successful!</p>
                <p className="text-xs text-emerald-600">Processing document...</p>
              </div>
            </div>
          )}

          {/* Error State */}
          {uploadStatus === 'error' && (
            <div className="mt-4 p-4 bg-rose-50 border border-rose-200 rounded-lg flex items-center gap-3">
              <AlertCircle size={20} className="text-rose-600" />
              <div>
                <p className="font-medium text-rose-800 text-sm">Upload failed</p>
                <p className="text-xs text-rose-600">Please try again</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t border-slate-200">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 border border-slate-200 rounded-lg font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!selectedFile || isLoading || uploadStatus === 'uploading'}
            className="px-6 py-2 text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
            style={{ backgroundColor: COLORS.primary }}
          >
            {isLoading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      </div>
    </div>
  );
}
