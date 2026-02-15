'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppSelector } from '@/store/hooks';
import { isClient, isTokenExpired } from '@/lib/utils';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, accessToken } = useAppSelector(state => state.auth);

  useEffect(() => {
    if (!isClient()) return;

    const token = accessToken || localStorage.getItem('access_token');
    
    if (!token || isTokenExpired(token)) {
      router.push('/login');
    }
  }, [isAuthenticated, accessToken, router]);

  if (!isAuthenticated && !localStorage.getItem('access_token')) {
    return null;
  }

  return <>{children}</>;
}
