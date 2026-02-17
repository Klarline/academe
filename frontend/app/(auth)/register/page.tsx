'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Mail, Lock, User, ArrowRight, AlertCircle, CheckCircle } from 'lucide-react';
import { COLORS } from '@/lib/constants';
import { useRegisterMutation } from '@/store/api/authApi';
import { useAppDispatch } from '@/store/hooks';
import { setCredentials } from '@/store/slices/authSlice';
import toast from 'react-hot-toast';

export default function RegisterPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const [register, { isLoading }] = useRegisterMutation();
  
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [emailError, setEmailError] = useState('');
  const [usernameError, setUsernameError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [confirmError, setConfirmError] = useState('');

  // Validate email
  useEffect(() => {
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setEmailError('Please enter a valid email address');
    } else {
      setEmailError('');
    }
  }, [email]);

  // Validate username
  useEffect(() => {
    if (username && username.length < 3) {
      setUsernameError('Username must be at least 3 characters');
    } else if (username && !/^[a-zA-Z0-9_-]+$/.test(username)) {
      setUsernameError('Only letters, numbers, underscores, and hyphens allowed');
    } else {
      setUsernameError('');
    }
  }, [username]);

  // Validate password strength
  useEffect(() => {
    if (password && password.length < 6) {
      setPasswordError('Password must be at least 6 characters');
    } else {
      setPasswordError('');
    }
  }, [password]);

  // Validate password match
  useEffect(() => {
    if (confirmPassword && password !== confirmPassword) {
      setConfirmError('Passwords do not match');
    } else {
      setConfirmError('');
    }
  }, [password, confirmPassword]);

  const hasErrors = emailError || usernameError || passwordError || confirmError;
  const isFormValid = email && username && password && confirmPassword && !hasErrors;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid) return;
    
    try {
      const result = await register({ email, username, password }).unwrap();
      dispatch(setCredentials({
        accessToken: result.access_token,
        refreshToken: result.refresh_token,
        userId: result.user_id
      }));
      toast.success('Account created successfully!');
      router.push('/onboarding');
    } catch (error: any) {
      const errorMessage = typeof error?.data === 'string'
        ? error.data
        : error?.data?.detail || error?.message || 'Registration failed. Please try again.';
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
          Create Your Account
        </h1>
        <p className="text-slate-600 mt-2">Join academe and start learning smarter</p>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Email Field */}
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
            {email && !emailError && (
              <div className="flex items-center gap-1.5 mt-2 text-emerald-600">
                <CheckCircle size={14} />
                <span className="text-xs font-medium">Valid email</span>
              </div>
            )}
          </div>

          {/* Username Field */}
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Username</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="john_student"
                className={`w-full pl-10 pr-4 py-2.5 border rounded-lg outline-none transition-all ${
                  usernameError 
                    ? 'border-rose-300 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500' 
                    : 'border-slate-200 focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500'
                }`}
              />
            </div>
            {usernameError && (
              <div className="flex items-start gap-2 mt-2 p-2.5 bg-rose-50 border border-rose-200 rounded-lg">
                <AlertCircle size={16} className="text-rose-600 mt-0.5 shrink-0" />
                <p className="text-sm text-rose-700">{usernameError}</p>
              </div>
            )}
            {username && !usernameError && (
              <div className="flex items-center gap-1.5 mt-2 text-emerald-600">
                <CheckCircle size={14} />
                <span className="text-xs font-medium">Valid username</span>
              </div>
            )}
          </div>

          {/* Password Field */}
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className={`w-full pl-10 pr-4 py-2.5 border rounded-lg outline-none transition-all ${
                  passwordError 
                    ? 'border-rose-300 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500' 
                    : 'border-slate-200 focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500'
                }`}
              />
            </div>
            {passwordError && (
              <div className="flex items-start gap-2 mt-2 p-2.5 bg-rose-50 border border-rose-200 rounded-lg">
                <AlertCircle size={16} className="text-rose-600 mt-0.5 shrink-0" />
                <p className="text-sm text-rose-700">{passwordError}</p>
              </div>
            )}
            {password && !passwordError && (
              <div className="flex items-center gap-1.5 mt-2 text-emerald-600">
                <CheckCircle size={14} />
                <span className="text-xs font-medium">Strong password</span>
              </div>
            )}
          </div>

          {/* Confirm Password Field */}
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Confirm Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className={`w-full pl-10 pr-4 py-2.5 border rounded-lg outline-none transition-all ${
                  confirmError 
                    ? 'border-rose-300 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500' 
                    : 'border-slate-200 focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500'
                }`}
              />
            </div>
            {confirmError && (
              <div className="flex items-start gap-2 mt-2 p-2.5 bg-rose-50 border border-rose-200 rounded-lg">
                <AlertCircle size={16} className="text-rose-600 mt-0.5 shrink-0" />
                <p className="text-sm text-rose-700">{confirmError}</p>
              </div>
            )}
            {confirmPassword && !confirmError && (
              <div className="flex items-center gap-1.5 mt-2 text-emerald-600">
                <CheckCircle size={14} />
                <span className="text-xs font-medium">Passwords match</span>
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading || !!hasErrors || !isFormValid}
            className="w-full py-3 text-white rounded-xl font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center justify-center gap-2"
            style={{ backgroundColor: COLORS.primary }}
          >
            {isLoading ? 'Creating account...' : 'Create Account'}
            {!isLoading && <ArrowRight size={18} />}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-slate-600 text-sm">
            Already have an account?{' '}
            <Link href="/login" className="font-semibold hover:underline" style={{ color: COLORS.primary }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
