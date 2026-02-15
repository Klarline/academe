'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppSelector } from '@/store/hooks';
import { isClient } from '@/lib/utils';

export default function Home() {
  const router = useRouter();
  const { isAuthenticated } = useAppSelector(state => state.auth);

  useEffect(() => {
    if (!isClient()) return;

    const token = localStorage.getItem('access_token');
    
    if (token && isAuthenticated) {
      router.push('/dashboard');
    } else {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sage-500 mx-auto mb-4" />
        <p className="text-slate-600">Loading...</p>
      </div>
    </div>
  );
}
