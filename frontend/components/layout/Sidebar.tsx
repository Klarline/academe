'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  BookOpen,
  Settings,
  X,
  ChevronLeft,
  ChevronRight,
  History,
  Plus,
  Search,
} from 'lucide-react';
import { COLORS } from '@/lib/constants';
import { cn, truncate, formatRelativeTime, getInitials } from '@/lib/utils';
import { useGetConversationsQuery } from '@/store/api/chatApi';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setCurrentConversation } from '@/store/slices/chatSlice';
import { useUserProfile } from '@/hooks/useUserProfile';

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  isCollapsed: boolean;
  toggleCollapse: () => void;
}

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
  { id: 'chat', label: 'AI Assistant', icon: MessageSquare, href: '/chat' },
  { id: 'research', label: 'Research', icon: Search, href: '/research' },
  { id: 'documents', label: 'Documents', icon: FileText, href: '/documents' },
  { id: 'practice', label: 'Practice Mode', icon: BookOpen, href: '/practice' },
  { id: 'settings', label: 'Settings', icon: Settings, href: '/settings' },
];

export default function Sidebar({ isOpen, setIsOpen, isCollapsed, toggleCollapse }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { isAuthenticated } = useAppSelector(state => state.auth);
  const { profile } = useUserProfile();
  
  // Fetch conversations only if authenticated
  const { data: conversationsData = [], isLoading } = useGetConversationsQuery(undefined, {
    skip: !isAuthenticated
  });

  // Safely extract conversations array
  const conversations = Array.isArray(conversationsData) 
    ? conversationsData 
    : (conversationsData?.conversations || []);

  const handleNewChat = () => {
    dispatch(setCurrentConversation(null));
    router.push('/chat');
    setIsOpen(false);
  };

  const handleConversationClick = (conversationId: string) => {
    dispatch(setCurrentConversation(conversationId));
    router.push('/chat');
    setIsOpen(false);
  };

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-20 md:hidden backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />
      )}
      
      {/* Sidebar Container */}
      <div 
        className={cn(
          "fixed inset-y-0 left-0 z-30",
          isCollapsed ? "w-20" : "w-72",
          "text-white transform transition-all duration-300 ease-in-out",
          "flex flex-col shadow-2xl",
          "md:relative md:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
        style={{ backgroundColor: COLORS.dark }}
      >
        {/* Logo Area */}
        <div className="p-5 flex items-center justify-between border-b border-white/10 h-16">
          <div className={cn("flex items-center gap-3", isCollapsed && "justify-center w-full")}>
            <div 
              className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-2xl shadow-lg transition-all"
              style={{ backgroundColor: COLORS.primary, fontFamily: "'Playfair Display', serif" }}
            >
              à
            </div>
            {!isCollapsed && (
              <h1 
                className="text-2xl font-bold text-white tracking-wide animate-in fade-in duration-300"
                style={{ fontFamily: "'Playfair Display', serif" }}
              >
                academe
              </h1>
            )}
          </div>
          
          <button onClick={() => setIsOpen(false)} className="md:hidden text-slate-400 hover:text-white transition-colors">
            <X size={24} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-6 space-y-2 overflow-y-auto scrollbar-hide">
          {menuItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            
            return (
              <Link
                key={item.id}
                href={item.href}
                onClick={() => setIsOpen(false)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 group relative",
                  isActive ? "text-white shadow-lg" : "text-slate-400 hover:bg-white/5 hover:text-white",
                  isCollapsed && "justify-center"
                )}
                style={isActive ? { backgroundColor: COLORS.primary } : {}}
                title={isCollapsed ? item.label : undefined}
              >
                <Icon size={22} className={cn("shrink-0 transition-transform duration-300", isActive && !isCollapsed && "scale-110")} />
                {!isCollapsed && <span className="font-medium tracking-wide truncate">{item.label}</span>}
                {isActive && !isCollapsed && (
                  <div className="absolute right-2 w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                )}
              </Link>
            );
          })}

          {/* Conversation History Section */}
          {!isCollapsed && isAuthenticated && (
            <div className="mt-8 pt-6 border-t border-white/10">
              <div className="px-3 mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <History size={12} className="text-slate-500" />
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Recent Chats</span>
                </div>
                <button
                  onClick={handleNewChat}
                  className="p-1 hover:bg-white/10 rounded transition-colors"
                  title="New Chat"
                >
                  <Plus size={14} className="text-slate-400" />
                </button>
              </div>

              <div className="space-y-1">
                {isLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map(i => (
                      <div key={i} className="h-10 bg-white/5 rounded-lg animate-pulse" />
                    ))}
                  </div>
                ) : conversations.length === 0 ? (
                  <div className="px-4 py-3 text-xs text-slate-500 text-center">
                    No conversations yet
                  </div>
                ) : (
                  conversations.slice(0, 10).map(conv => (
                    <button
                      key={conv.id}
                      onClick={() => handleConversationClick(conv.id)}
                      className="w-full text-left px-4 py-2.5 text-sm text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition-all truncate flex items-start gap-2 group"
                    >
                      <MessageSquare size={14} className="opacity-50 group-hover:opacity-100 mt-0.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="truncate font-medium">{conv.title}</div>
                        <div className="text-xs text-slate-500 truncate">{formatRelativeTime(conv.updated_at)}</div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </nav>

        {/* User Profile Footer */}
        <div className="p-4 border-t border-white/10 bg-black/20">
          <Link
            href="/settings"
            onClick={() => setIsOpen(false)}
            className={cn(
              "flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 transition-colors",
              isCollapsed && "justify-center"
            )}
          >
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#90AB8B] to-[#5A7863] flex items-center justify-center text-xs font-bold text-white shadow-inner shrink-0 border border-white/20">
              {profile ? getInitials(profile.username) : 'U'}
            </div>
            {!isCollapsed && (
              <div className="flex-1 overflow-hidden">
                <p className="text-sm font-semibold text-slate-200 truncate">
                  {profile?.username || 'Loading...'}
                </p>
                <p className="text-xs text-slate-400 truncate">Student</p>
              </div>
            )}
            {!isCollapsed && <Settings size={16} className="text-slate-500" />}
          </Link>
        </div>
        
        <button 
          onClick={toggleCollapse}
          className="hidden md:flex absolute -right-3 top-20 w-6 h-6 border border-white/20 rounded-full items-center justify-center text-slate-400 hover:text-white transition-all shadow-md z-50"
          style={{ backgroundColor: COLORS.dark }}
          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = COLORS.primary}
          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = COLORS.dark}
        >
          {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>
    </>
  );
}
