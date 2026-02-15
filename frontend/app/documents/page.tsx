'use client';

import React, { useState } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import UploadModal from '@/components/documents/UploadModal';
import { UploadCloud, FileText, Trash2, Loader2 } from 'lucide-react';
import { COLORS } from '@/lib/constants';
import { formatFileSize, formatRelativeTime } from '@/lib/utils';
import { useGetDocumentsQuery, useDeleteDocumentMutation } from '@/store/api/documentApi';
import toast from 'react-hot-toast';

export default function DocumentsPage() {
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const { data: documents = [], isLoading, refetch } = useGetDocumentsQuery();
  const [deleteDocument, { isLoading: isDeleting }] = useDeleteDocumentMutation();

  // Ensure documents is always an array
  const documentList = Array.isArray(documents) ? documents : [];

  const handleDelete = async (id: string, filename: string) => {
    if (confirm(`Delete "${filename}"?`)) {
      try {
        await deleteDocument(id).unwrap();
        toast.success('Document deleted');
        refetch();
      } catch (error) {
        toast.error('Failed to delete document');
      }
    }
  };

  return (
    <MainLayout>
      <div className="space-y-6 animate-in fade-in duration-500">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-slate-800" style={{ fontFamily: "'Playfair Display', serif" }}>
              My Documents
            </h2>
            <p className="text-slate-600 text-sm mt-1">
              {isLoading ? 'Loading...' : `${documentList.length} documents uploaded`}
            </p>
          </div>
          
          <button 
            onClick={() => setIsUploadModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 text-white rounded-xl hover:opacity-90 transition-all shadow-sm font-medium"
            style={{ backgroundColor: COLORS.primary }}
          >
            <UploadCloud size={18} />
            <span>Upload Document</span>
          </button>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center">
              <Loader2 size={32} className="animate-spin mx-auto text-sage-500 mb-2" />
              <p className="text-slate-600">Loading documents...</p>
            </div>
          ) : documentList.length === 0 ? (
            <div className="p-12 text-center">
              <div 
                className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
                style={{ backgroundColor: `${COLORS.secondary}20`, color: COLORS.primary }}
              >
                <FileText size={32} />
              </div>
              <h3 className="text-lg font-semibold text-slate-800 mb-2">No documents yet</h3>
              <p className="text-slate-600 text-sm mb-6">Upload your study materials to get started</p>
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="px-6 py-2.5 text-white rounded-xl hover:opacity-90 transition-all shadow-sm font-medium"
                style={{ backgroundColor: COLORS.primary }}
              >
                Upload Your First Document
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                      Document
                    </th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                      Size
                    </th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                      Uploaded
                    </th>
                    <th className="text-right px-6 py-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {documentList.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-lg bg-slate-100">
                            <FileText size={18} className="text-slate-600" />
                          </div>
                          <div>
                            <span className="font-medium text-slate-800 block">{doc.filename}</span>
                            {doc.upload_status === 'processing' && (
                              <span className="text-xs text-yellow-600 flex items-center gap-1">
                                <Loader2 size={10} className="animate-spin" />
                                Processing...
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-600 text-sm">
                        {formatFileSize(doc.file_size)}
                      </td>
                      <td className="px-6 py-4 text-slate-600 text-sm">
                        {formatRelativeTime(doc.created_at)}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button 
                          onClick={() => handleDelete(doc.id, doc.filename)}
                          disabled={isDeleting}
                          className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors disabled:opacity-50"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <UploadModal isOpen={isUploadModalOpen} onClose={() => setIsUploadModalOpen(false)} />
    </MainLayout>
  );
}
