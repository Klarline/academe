'use client';

import React, { useState } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import { Search, BookOpen, FileText, Loader2, ExternalLink } from 'lucide-react';
import { COLORS } from '@/lib/constants';
import { useAskResearchQuestionMutation } from '@/store/api/researchApi';
import { ResearchResponse } from '@/store/api/researchApi';
import toast from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';

export default function ResearchPage() {
  const [askQuestion, { isLoading }] = useAskResearchQuestionMutation();
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<ResearchResponse | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) {
      toast.error('Please enter a question');
      return;
    }

    try {
      const response = await askQuestion({ 
        query: query.trim(), 
        top_k: 5,
        use_citations: true 
      }).unwrap();
      setResult(response);
    } catch (error: any) {
      toast.error(error?.data?.detail || 'Research failed');
    }
  };

  return (
    <MainLayout>
      <div className="max-w-5xl mx-auto space-y-6 py-8">
        <div className="text-center mb-8">
          <div className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg" 
            style={{ backgroundColor: `${COLORS.secondary}20`, color: COLORS.primary }}>
            <Search size={32} />
          </div>
          <h2 className="text-3xl font-bold text-slate-800 mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>
            Research Your Documents
          </h2>
          <p className="text-slate-600">Ask questions about your uploaded materials and get AI-powered answers with citations</p>
        </div>

        {/* Search Bar */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !isLoading && handleSearch()}
              placeholder="Ask a question about your documents..."
              className="flex-1 px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500 outline-none"
            />
            <button
              onClick={handleSearch}
              disabled={isLoading || !query.trim()}
              className="px-6 py-3 text-white rounded-xl font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center gap-2"
              style={{ backgroundColor: COLORS.primary }}
            >
              {isLoading ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  Researching...
                </>
              ) : (
                <>
                  <Search size={20} />
                  Ask
                </>
              )}
            </button>
          </div>
        </div>

        {/* Answer and Sources */}
        {result && (
          <div className="space-y-6">
            {/* Answer */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
              <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
                <BookOpen size={20} className="text-purple-600" />
                Answer
              </h3>
              <div className="prose prose-slate max-w-none">
                <ReactMarkdown>{result.answer}</ReactMarkdown>
              </div>
              {result.processing_time_ms && (
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <p className="text-xs text-slate-500">
                    Generated in {(result.processing_time_ms / 1000).toFixed(2)}s by {result.agent_used}
                  </p>
                </div>
              )}
            </div>

            {/* Sources */}
            {result.sources && result.sources.length > 0 && (
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
                  <FileText size={20} className="text-purple-600" />
                  Sources ({result.sources.length})
                </h3>
                <div className="space-y-3">
                  {result.sources.map((source, index) => (
                    <div 
                      key={index} 
                      className="p-4 bg-slate-50 rounded-lg border border-slate-100 hover:border-purple-200 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <FileText size={16} className="text-purple-600" />
                          <span className="font-medium text-slate-800 text-sm">
                            {source.filename}
                          </span>
                        </div>
                        <span className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded-full">
                          {(source.relevance_score * 100).toFixed(0)}% match
                        </span>
                      </div>
                      {(source.page_number || source.section_title) && (
                        <div className="flex gap-2 mb-2 text-xs text-slate-600">
                          {source.page_number && (
                            <span>Page {source.page_number}</span>
                          )}
                          {source.section_title && (
                            <span>• {source.section_title}</span>
                          )}
                        </div>
                      )}
                      <p className="text-slate-600 text-sm leading-relaxed">
                        {source.excerpt}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Empty State */}
        {!result && !isLoading && (
          <div className="text-center py-16 bg-white rounded-2xl border border-slate-200">
            <BookOpen size={48} className="mx-auto mb-4 text-slate-300" />
            <p className="text-slate-600 mb-2">Ask a question to get started</p>
            <p className="text-slate-400 text-sm">
              Your documents will be searched and analyzed to provide comprehensive answers
            </p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
