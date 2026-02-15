import { baseApi } from './baseApi';
import { 
  UserProfile, 
  UserStats, 
  UpdateUserProfileRequest,
  CompleteOnboardingRequest 
} from '@/types/user';
import { API_ENDPOINTS } from '@/lib/constants';

export const userApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getProfile: builder.query<UserProfile, void>({
      query: () => API_ENDPOINTS.USERS.ME,
      providesTags: ['User'],
    }),
    updateProfile: builder.mutation<UserProfile, UpdateUserProfileRequest>({
      query: (updates) => ({
        url: API_ENDPOINTS.USERS.UPDATE,
        method: 'PUT',
        body: updates,
      }),
      invalidatesTags: ['User'],
    }),
    getStats: builder.query<UserStats, void>({
      query: () => API_ENDPOINTS.USERS.STATS,
    }),
    completeOnboarding: builder.mutation<UserProfile, CompleteOnboardingRequest>({
      query: (data) => ({
        url: API_ENDPOINTS.USERS.COMPLETE_ONBOARDING,
        method: 'POST',
        body: data,
      }),
      invalidatesTags: ['User'],
    }),
  }),
});

export const {
  useGetProfileQuery,
  useUpdateProfileMutation,
  useGetStatsQuery,
  useCompleteOnboardingMutation,
} = userApi;
