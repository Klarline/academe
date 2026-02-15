import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { useGetProfileQuery } from '@/store/api/userApi';
import { setProfile } from '@/store/slices/userSlice';

export function useUserProfile() {
  const dispatch = useAppDispatch();
  const { isAuthenticated } = useAppSelector(state => state.auth);
  const { profile } = useAppSelector(state => state.user);
  
  const { data: fetchedProfile, isLoading } = useGetProfileQuery(undefined, {
    skip: !isAuthenticated
  });

  useEffect(() => {
    if (fetchedProfile) {
      dispatch(setProfile(fetchedProfile));
    }
  }, [fetchedProfile, dispatch]);

  return {
    profile,
    isLoading
  };
}
