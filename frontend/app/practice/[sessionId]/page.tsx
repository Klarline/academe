'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import MainLayout from '@/components/layout/MainLayout';
import { ArrowLeft, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { COLORS } from '@/lib/constants';
import { useGetPracticeSessionQuery } from '@/store/api/practiceApi';

export default function SessionReviewPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;
  const { data: session, isLoading } = useGetPracticeSessionQuery(sessionId);

  if (isLoading) {
    return (
      <MainLayout>
        <div className="max-w-3xl mx-auto py-8">
          <div className="flex items-center justify-center h-64">
            <Loader2 size={40} className="animate-spin text-sage-500" />
          </div>
        </div>
      </MainLayout>
    );
  }

  if (!session) {
    return (
      <MainLayout>
        <div className="text-center py-16">
          <h3 className="text-xl font-bold text-slate-800 mb-4">Session not found</h3>
          <button onClick={() => router.push('/practice/history')} className="px-6 py-3 text-white rounded-xl font-semibold hover:opacity-90 transition-all" style={{ backgroundColor: COLORS.primary }}>
            Back to History
          </button>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-3xl mx-auto space-y-6 py-8">
        <button onClick={() => router.push('/practice/history')} className="flex items-center gap-2 text-slate-600 hover:text-slate-800 font-medium transition-colors">
          <ArrowLeft size={20} />
          Back to History
        </button>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
          <h2 className="text-2xl font-bold text-slate-800 mb-6">{session.topic}</h2>
          
          <div className="grid grid-cols-4 gap-4 mb-8">
            <div className="text-center p-4 bg-slate-50 rounded-xl">
              <div className="text-2xl font-bold text-slate-800">{session.percentage}%</div>
              <div className="text-sm text-slate-600">Score</div>
            </div>
            <div className="text-center p-4 bg-slate-50 rounded-xl">
              <div className="text-2xl font-bold text-slate-800">{session.score}/{session.total_questions}</div>
              <div className="text-sm text-slate-600">Correct</div>
            </div>
            <div className="text-center p-4 bg-slate-50 rounded-xl">
              <div className="text-2xl font-bold text-slate-800">{session.duration_minutes}m</div>
              <div className="text-sm text-slate-600">Duration</div>
            </div>
            <div className="text-center p-4 bg-slate-50 rounded-xl">
              <div className="text-2xl font-bold text-slate-800">{session.total_questions}</div>
              <div className="text-sm text-slate-600">Questions</div>
            </div>
          </div>

          <div className="space-y-6">
            <h3 className="text-lg font-bold text-slate-800">Questions Review</h3>
            {session.questions.map((q: any, i: number) => (
              <div key={i} className={`p-6 rounded-xl border-2 ${q.is_correct ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200'}`}>
                <div className="flex items-start gap-3 mb-4">
                  {q.is_correct ? <CheckCircle size={24} className="text-emerald-600 mt-1 shrink-0" /> : <XCircle size={24} className="text-rose-600 mt-1 shrink-0" />}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <p className="font-bold text-slate-800">Question {i + 1}</p>
                      <span className="px-2 py-0.5 bg-white/50 text-xs font-semibold rounded-full uppercase">{q.type}</span>
                    </div>
                    <p className="text-slate-700 leading-relaxed">{q.question}</p>
                  </div>
                </div>

                {q.type === 'mcq' && q.options && (
                  <div className="space-y-2 mb-4 ml-9">
                    {q.options.map((opt: string, j: number) => {
                      const isCorrect = opt === q.correct_answer;
                      const isUserAnswer = opt === q.user_answer;
                      return (
                        <div key={j} className={`p-3 rounded-lg border-2 ${isCorrect ? 'bg-emerald-100 border-emerald-400' : isUserAnswer ? 'bg-rose-100 border-rose-400' : 'bg-white border-slate-200'}`}>
                          <div className="flex items-center justify-between">
                            <span>{opt}</span>
                            {isCorrect && <span className="text-emerald-600 font-semibold text-sm">✓ Correct</span>}
                            {isUserAnswer && !isCorrect && <span className="text-rose-600 font-semibold text-sm">✗ Your Answer</span>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {q.type !== 'mcq' && (
                  <div className="ml-9 space-y-3">
                    <div>
                      <p className="text-sm font-medium text-slate-600 mb-1">Your Answer:</p>
                      <div className={`p-3 rounded-lg border-2 ${q.is_correct ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200'}`}>
                        <p className="text-slate-700 whitespace-pre-wrap">{q.user_answer || '(No answer provided)'}</p>
                      </div>
                    </div>
                    {!q.is_correct && (
                      <div>
                        <p className="text-sm font-medium text-slate-600 mb-1">Correct Answer:</p>
                        <div className="bg-emerald-50 p-3 rounded-lg border-2 border-emerald-200">
                          <p className="text-slate-700 whitespace-pre-wrap">{q.correct_answer}</p>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {q.explanation && (
                  <div className="ml-9 mt-4 p-4 bg-white rounded-lg border border-slate-300">
                    <p className="text-sm font-medium text-slate-600 mb-2">💡 Explanation:</p>
                    <p className="text-slate-700 text-sm leading-relaxed">{q.explanation}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
