'use client';

import React from 'react';
import MainLayout from '@/components/layout/MainLayout';
import { Trash2, Eye, BookOpen, Loader2 } from 'lucide-react';
import { COLORS } from '@/lib/constants';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { useGetPracticeSessionsQuery, useDeletePracticeSessionMutation } from '@/store/api/practiceApi';

export default function PracticeHistoryPage() {
  const { data: sessions = [], isLoading, refetch } = useGetPracticeSessionsQuery({});
  const [deleteSession] = useDeletePracticeSessionMutation();

  const handleDelete = async (sessionId: string) => {
    if (confirm('Delete this practice session?')) {
      try {
        await deleteSession(sessionId).unwrap();
        toast.success('Session deleted');
        refetch();
      } catch (error) {
        toast.error('Failed to delete session');
      }
    }
  };

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
    return `${Math.floor(days / 30)} months ago`;
  };

  return (
    <MainLayout>
      <div className="max-w-5xl mx-auto space-y-6 py-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold text-slate-800 mb-2">Practice History</h2>
            <p className="text-slate-600">Review your past practice sessions</p>
          </div>
          <Link href="/practice" className="px-6 py-3 text-white rounded-xl font-semibold hover:opacity-90 transition-all shadow-sm" style={{ backgroundColor: COLORS.primary }}>
            New Practice Session
          </Link>
        </div>

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white rounded-xl p-6 animate-pulse">
                <div className="h-6 bg-slate-200 rounded w-1/3 mb-4" />
                <div className="h-4 bg-slate-200 rounded w-1/4" />
              </div>
            ))}
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-slate-200">
            <BookOpen size={64} className="mx-auto mb-4 text-slate-300" />
            <h3 className="text-xl font-bold text-slate-800 mb-2">No Practice History Yet</h3>
            <p className="text-slate-600 mb-6">Complete a practice session to see it here</p>
            <Link href="/practice" className="inline-flex items-center gap-2 px-6 py-3 text-white rounded-xl font-semibold hover:opacity-90 transition-all" style={{ backgroundColor: COLORS.primary }}>
              Start Practicing
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {sessions.map((session: any) => (
              <div key={session.id} className="bg-white rounded-xl border border-slate-200 p-6 hover:shadow-md transition-all">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-slate-800">{session.topic}</h3>
                    <div className="flex items-center gap-4 mt-2 text-sm text-slate-600">
                      <span>{formatRelativeTime(session.completed_at)}</span>
                      <span>•</span>
                      <span>{session.duration_minutes} minutes</span>
                      <span>•</span>
                      <span>{session.total_questions} questions</span>
                    </div>
                  </div>
                  <div className={`text-2xl font-bold ${session.percentage >= 70 ? 'text-emerald-600' : session.percentage >= 50 ? 'text-amber-600' : 'text-rose-600'}`}>
                    {session.percentage}%
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Link href={`/practice/${session.id}`} className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors text-sm font-medium">
                    <Eye size={16} />
                    Review
                  </Link>
                  <button onClick={() => handleDelete(session.id)} className="flex items-center gap-2 px-4 py-2 border border-rose-200 text-rose-600 rounded-lg hover:bg-rose-50 transition-colors text-sm font-medium">
                    <Trash2 size={16} />
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </MainLayout>
  );
}
