import { useEffect } from 'react';
import { useAppDispatch } from '@/store/hooks';
import { setCredentials } from '@/store/slices/authSlice';
import { isClient, isTokenExpired } from '@/lib/utils';

export function useAuthInit() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (!isClient()) return;

    const accessToken = localStorage.getItem('access_token');
    const refreshToken = localStorage.getItem('refresh_token');
    const userId = localStorage.getItem('user_id');

    if (accessToken && userId && !isTokenExpired(accessToken)) {
      dispatch(setCredentials({
        accessToken,
        refreshToken: refreshToken || undefined,
        userId
      }));
    } else {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user_id');
    }
  }, [dispatch]);
}
