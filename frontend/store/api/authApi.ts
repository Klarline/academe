import { baseApi } from './baseApi';
import { LoginRequest, RegisterRequest, AuthResponse } from '@/types/auth';
import { API_ENDPOINTS } from '@/lib/constants';

export const authApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    login: builder.mutation<AuthResponse, LoginRequest>({
      query: (credentials) => ({
        url: API_ENDPOINTS.AUTH.LOGIN,
        method: 'POST',
        body: {
          email_or_username: credentials.email,
          password: credentials.password
        },
      }),
      transformErrorResponse: (response: any) => {
        if (response.data?.detail) {
          if (Array.isArray(response.data.detail)) {
            return response.data.detail[0].msg || 'Validation error';
          }
          return response.data.detail;
        }
        return 'Login failed';
      },
    }),
    register: builder.mutation<AuthResponse, RegisterRequest>({
      query: (userData) => ({
        url: API_ENDPOINTS.AUTH.REGISTER,
        method: 'POST',
        body: userData,
      }),
      transformErrorResponse: (response: any) => {
        if (response.data?.detail) {
          if (Array.isArray(response.data.detail)) {
            return response.data.detail[0].msg || 'Validation error';
          }
          return response.data.detail;
        }
        return 'Registration failed';
      },
    }),
    logout: builder.mutation<void, void>({
      query: () => ({
        url: API_ENDPOINTS.AUTH.LOGOUT,
        method: 'POST',
      }),
    }),
  }),
});

export const {
  useLoginMutation,
  useRegisterMutation,
  useLogoutMutation,
} = authApi;
