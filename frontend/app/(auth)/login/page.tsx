'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Mail, Lock, ArrowRight, AlertCircle } from 'lucide-react';
import { COLORS } from '@/lib/constants';
import { useLoginMutation } from '@/store/api/authApi';
import { useAppDispatch } from '@/store/hooks';
import { setCredentials } from '@/store/slices/authSlice';
import toast from 'react-hot-toast';

export default function LoginPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const [login, { isLoading }] = useLoginMutation();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailError, setEmailError] = useState('');

  useEffect(() => {
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setEmailError('Please enter a valid email address');
    } else {
      setEmailError('');
    }
  }, [email]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (emailError) return;
    
    try {
      const result = await login({ email, password }).unwrap();
      
      dispatch(setCredentials({
        accessToken: result.access_token,
        refreshToken: result.refresh_token,
        userId: result.user_id
      }));
      
      toast.success('Welcome back!');
      router.push('/dashboard');
    } catch (error: any) {
      const errorMessage = typeof error?.data === 'string' 
        ? error.data 
        : error?.data?.detail || error?.message || 'Login failed. Please check your credentials.';
      toast.error(errorMessage);
    }
  };

  return (
    <div className="w-full max-w-md">
      <div className="text-center mb-8">
        <div 
          className="w-16 h-16 rounded-2xl flex items-center justify-center text-white font-bold text-3xl shadow-lg mx-auto mb-4"
          style={{ backgroundColor: COLORS.primary, fontFamily: "'Playfair Display', serif" }}
        >
          à
        </div>
        <h1 className="text-3xl font-bold text-slate-800" style={{ fontFamily: "'Playfair Display', serif" }}>
          Welcome to Academe
        </h1>
        <p className="text-slate-600 mt-2">Sign in to continue your learning journey</p>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@northeastern.edu"
                className={`w-full pl-10 pr-4 py-2.5 border rounded-lg outline-none transition-all ${
                  emailError 
                    ? 'border-rose-300 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500' 
                    : 'border-slate-200 focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500'
                }`}
              />
            </div>
            {emailError && (
              <div className="flex items-start gap-2 mt-2 p-2.5 bg-rose-50 border border-rose-200 rounded-lg">
                <AlertCircle size={16} className="text-rose-600 mt-0.5 shrink-0" />
                <p className="text-sm text-rose-700">{emailError}</p>
              </div>
            )}
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500 outline-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading || !!emailError}
            className="w-full py-3 text-white rounded-xl font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center justify-center gap-2"
            style={{ backgroundColor: COLORS.primary }}
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
            {!isLoading && <ArrowRight size={18} />}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-slate-600 text-sm">
            Don&apos;t have an account?{' '}
            <Link href="/register" className="font-semibold hover:underline" style={{ color: COLORS.primary }}>
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
