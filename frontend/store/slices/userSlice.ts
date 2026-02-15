import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { UserProfile, UserStats } from '@/types/user';

interface UserState {
  profile: UserProfile | null;
  stats: UserStats | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: UserState = {
  profile: null,
  stats: null,
  isLoading: false,
  error: null,
};

const userSlice = createSlice({
  name: 'user',
  initialState,
  reducers: {
    setProfile: (state, action: PayloadAction<UserProfile>) => {
      state.profile = action.payload;
      state.error = null;
    },
    updateProfile: (state, action: PayloadAction<Partial<UserProfile>>) => {
      if (state.profile) {
        state.profile = { ...state.profile, ...action.payload };
      }
    },
    setStats: (state, action: PayloadAction<UserStats>) => {
      state.stats = action.payload;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
      state.isLoading = false;
    },
    clearUser: (state) => {
      state.profile = null;
      state.stats = null;
      state.error = null;
    },
  },
});

export const {
  setProfile,
  updateProfile,
  setStats,
  setLoading,
  setError,
  clearUser,
} = userSlice.actions;

export default userSlice.reducer;
