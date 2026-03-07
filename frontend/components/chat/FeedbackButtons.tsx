'use client';

import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { useSubmitFeedbackMutation } from '@/store/api/chatApi';

interface FeedbackButtonsProps {
  messageId: string;
  onSuccess?: () => void;
  onError?: (err: string) => void;
}

export default function FeedbackButtons({ messageId, onSuccess, onError }: FeedbackButtonsProps) {
  const [submitFeedback, { isLoading }] = useSubmitFeedbackMutation();
  const [selected, setSelected] = useState<1 | -1 | null>(null);

  const handleFeedback = async (rating: 1 | -1) => {
    if (selected !== null || isLoading) return;
    try {
      await submitFeedback({ message_id: messageId, rating }).unwrap();
      setSelected(rating);
      onSuccess?.();
    } catch (err: any) {
      onError?.(err?.data?.detail || 'Failed to submit feedback');
    }
  };

  return (
    <div className="flex items-center gap-1 mt-1">
      <button
        type="button"
        onClick={() => handleFeedback(1)}
        disabled={selected !== null || isLoading}
        className={`p-1 rounded transition-colors ${
          selected === 1
            ? 'text-emerald-600 bg-emerald-50'
            : 'text-slate-400 hover:text-emerald-600 hover:bg-slate-100'
        }`}
        aria-label="Thumbs up"
      >
        <ThumbsUp size={14} />
      </button>
      <button
        type="button"
        onClick={() => handleFeedback(-1)}
        disabled={selected !== null || isLoading}
        className={`p-1 rounded transition-colors ${
          selected === -1
            ? 'text-rose-600 bg-rose-50'
            : 'text-slate-400 hover:text-rose-600 hover:bg-slate-100'
        }`}
        aria-label="Thumbs down"
      >
        <ThumbsDown size={14} />
      </button>
    </div>
  );
}
