'use client';

import React, { useState } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import { Search, BookOpen, FileText, Loader2 } from 'lucide-react';
import { COLORS } from '@/lib/constants';
import { useSearchDocumentsMutation } from '@/store/api/documentApi';
import toast from 'react-hot-toast';

export default function ResearchPage() {
  const [searchDocs, { isLoading }] = useSearchDocumentsMutation();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any>(null);

  const handleSearch = async () => {
    if (!query.trim()) {
      toast.error('Please enter a search query');
      return;
    }

    try {
      const result = await searchDocs({ query: query.trim(), top_k: 5 }).unwrap();
      setResults(result);
    } catch (error: any) {
      toast.error(error?.data?.detail || 'Search failed');
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
          <p className="text-slate-600">Search across all your uploaded materials with AI-powered semantic search</p>
        </div>

        {/* Search Bar */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !isLoading && handleSearch()}
              placeholder="What would you like to know from your documents?"
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
                  Searching...
                </>
              ) : (
                <>
                  <Search size={20} />
                  Search
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results */}
        {results && (
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-slate-800">Search Results</h3>
            
            {results.results && results.results.length > 0 ? (
              <div className="space-y-4">
                {results.results.map((result: any, index: number) => (
                  <div key={index} className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-all">
                    <div className="flex items-start gap-3 mb-3">
                      <div className="p-2 bg-purple-50 rounded-lg">
                        <FileText size={18} className="text-purple-600" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-slate-800">{result.filename}</h4>
                        {result.page_number && (
                          <span className="text-xs text-slate-500">Page {result.page_number}</span>
                        )}
                      </div>
                      <span className="text-xs text-slate-400">
                        {(result.similarity_score * 100).toFixed(0)}% match
                      </span>
                    </div>
                    <p className="text-slate-700 leading-relaxed text-sm">
                      {result.chunk_text}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 bg-white rounded-xl border border-slate-200">
                <BookOpen size={48} className="mx-auto mb-4 text-slate-300" />
                <p className="text-slate-600">No results found. Try a different search term.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </MainLayout>
  );
}
