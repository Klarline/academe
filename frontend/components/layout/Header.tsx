'use client';

import React from 'react';
import { Menu, Bell, Search } from 'lucide-react';
import { COLORS } from '@/lib/constants';

interface HeaderProps {
  onMenuClick: () => void;
  title?: string;
}

export default function Header({ onMenuClick, title }: HeaderProps) {
  return (
    <header className="h-16 bg-white/80 backdrop-blur-md border-b border-slate-200 flex items-center justify-between px-4 md:px-8 z-10 shrink-0">
      {/* Left Section */}
      <div className="flex items-center gap-4">
        <button 
          onClick={onMenuClick}
          className="md:hidden p-2 text-slate-500 hover:bg-slate-100 rounded-lg transition-colors"
        >
          <Menu size={24} />
        </button>
        
        {title && (
          <h2 
            className="text-xl font-bold capitalize hidden md:block tracking-tight"
            style={{ color: COLORS.dark }}
          >
            {title}
          </h2>
        )}
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-4">
        {/* Search Bar (Desktop) */}
        <div className="hidden md:flex relative group">
          <Search 
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-sage-500 transition-colors" 
            size={16} 
          />
          <input 
            type="text" 
            placeholder="Search anything..." 
            className="pl-10 pr-4 py-2 bg-white border border-slate-200 focus:border-sage-500 rounded-full text-sm outline-none w-64 transition-all shadow-sm"
          />
        </div>
      </div>
    </header>
  );
}
