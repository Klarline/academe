'use client';

import React from 'react';
import MainLayout from '@/components/layout/MainLayout';
import { Clock, CheckCircle2, TrendingUp, Cpu, Loader2 } from 'lucide-react';
import { COLORS } from '@/lib/constants';
import { useGetStatsQuery } from '@/store/api/userApi';

export default function DashboardPage() {
  const { data: userStats, isLoading } = useGetStatsQuery();

  // Map backend stats to display format
  const stats = [
    { 
      label: 'Study Hours', 
      value: userStats?.total_study_time_hours?.toFixed(1) || '0', 
      change: '+12%', 
      icon: Clock 
    },
    { 
      label: 'Concepts Studied', 
      value: userStats?.concepts_studied?.toString() || '0', 
      change: '+5%', 
      icon: CheckCircle2 
    },
    { 
      label: 'Study Streak', 
      value: userStats?.study_streak_days?.toString() || '0', 
      change: '+24', 
      icon: TrendingUp 
    },
    { 
      label: 'Total Messages', 
      value: userStats?.total_messages?.toString() || '0', 
      change: userStats?.total_messages ? `${userStats.total_messages} total` : '0', 
      icon: Cpu 
    },
  ];

  return (
    <MainLayout>
      <div className="space-y-8 animate-in fade-in duration-500">
        {/* Welcome Section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 
              className="text-3xl font-bold mb-1"
              style={{ color: COLORS.dark, fontFamily: "'Playfair Display', serif" }}
            >
              Welcome back!
            </h2>
            <p className="text-slate-600 font-medium">
              {isLoading ? 'Loading your progress...' : 'Your learning progress is on track.'}
            </p>
          </div>
        </div>

        {/* Stats Grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 h-32">
                <div className="animate-pulse space-y-3">
                  <div className="flex justify-between">
                    <div className="w-12 h-12 bg-slate-200 rounded-xl" />
                    <div className="w-16 h-6 bg-slate-200 rounded-full" />
                  </div>
                  <div className="w-20 h-8 bg-slate-200 rounded" />
                  <div className="w-24 h-4 bg-slate-200 rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {stats.map((stat) => {
              const Icon = stat.icon;
              const isPositive = typeof stat.change === 'string' && stat.change.startsWith('+');
              
              return (
                <div
                  key={stat.label}
                  className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md hover:shadow-[#5A7863]/10 transition-all duration-300 group"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div 
                      className="p-3 rounded-xl group-hover:scale-110 transition-transform duration-300"
                      style={{ 
                        backgroundColor: `${COLORS.secondary}20`,
                        color: COLORS.primary
                      }}
                    >
                      <Icon size={24} />
                    </div>
                    
                    {typeof stat.change === 'string' && stat.change.includes('%') && (
                      <div className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                        isPositive ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-800'
                      }`}>
                        {stat.change}
                      </div>
                    )}
                  </div>
                  <div>
                    <h3 className="text-3xl font-bold mb-1" style={{ color: COLORS.dark }}>
                      {stat.value}
                    </h3>
                    <p className="text-sm text-slate-500 font-medium">{stat.label}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Quick Actions */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
          <h2 className="text-xl font-bold mb-4" style={{ color: COLORS.dark }}>
            Quick Actions
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <a
              href="/chat"
              className="p-6 border-2 border-slate-100 rounded-xl hover:border-[#5A7863] transition-all group bg-white"
            >
              <div className="font-semibold text-slate-800 group-hover:text-[#5A7863] transition-colors">
                Start New Chat
              </div>
              <p className="text-sm text-slate-500 mt-1">Ask questions and get explanations</p>
            </a>
            
            <a
              href="/research"
              className="p-6 border-2 border-slate-100 rounded-xl hover:border-[#5A7863] transition-all group bg-white"
            >
              <div className="font-semibold text-slate-800 group-hover:text-[#5A7863] transition-colors">
                Research Documents
              </div>
              <p className="text-sm text-slate-500 mt-1">Get answers with citations from your materials</p>
            </a>
            
            <a
              href="/documents"
              className="p-6 border-2 border-slate-100 rounded-xl hover:border-[#5A7863] transition-all group bg-white"
            >
              <div className="font-semibold text-slate-800 group-hover:text-[#5A7863] transition-colors">
                Upload Documents
              </div>
              <p className="text-sm text-slate-500 mt-1">
                {userStats ? `${userStats.documents_uploaded} documents uploaded` : 'Add your study materials'}
              </p>
            </a>
            
            <a
              href="/practice"
              className="p-6 border-2 border-slate-100 rounded-xl hover:border-[#5A7863] transition-all group bg-white"
            >
              <div className="font-semibold text-slate-800 group-hover:text-[#5A7863] transition-colors">
                Practice Mode
              </div>
              <p className="text-sm text-slate-500 mt-1">Test your knowledge</p>
            </a>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
