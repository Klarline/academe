'use client';

import React, { useState } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import { 
  User, 
  BookOpen, 
  Code, 
  FileText,
  Moon,
  Shield,
  LogOut,
  ChevronRight 
} from 'lucide-react';
import { COLORS, LearningLevel, LearningGoal, ExplanationStyle, RAGFallbackPreference } from '@/lib/constants';
import { useUserProfile } from '@/hooks/useUserProfile';
import { useUpdateProfileMutation } from '@/store/api/userApi';
import { getInitials } from '@/lib/utils';
import toast from 'react-hot-toast';

export default function SettingsPage() {
  const { profile } = useUserProfile();
  const [updateProfile, { isLoading: isSaving }] = useUpdateProfileMutation();
  
  const [learningLevel, setLearningLevel] = useState<LearningLevel>(
    profile?.learning_level || LearningLevel.INTERMEDIATE
  );
  const [learningGoal, setLearningGoal] = useState<LearningGoal>(
    profile?.learning_goal || LearningGoal.DEEP_LEARNING
  );
  const [explanationStyle, setExplanationStyle] = useState<ExplanationStyle>(
    profile?.explanation_style || ExplanationStyle.BALANCED
  );
  const [ragFallback, setRagFallback] = useState<RAGFallbackPreference>(
    profile?.rag_fallback_preference || RAGFallbackPreference.ALWAYS_ASK
  );
  const [includeMath, setIncludeMath] = useState(profile?.include_math_formulas ?? true);
  const [includeVisuals, setIncludeVisuals] = useState(profile?.include_visualizations ?? true);
  const [codeLanguage, setCodeLanguage] = useState(profile?.preferred_code_language || 'python');

  const handleSave = async () => {
    try {
      await updateProfile({
        learning_level: learningLevel,
        learning_goal: learningGoal,
        explanation_style: explanationStyle,
        rag_fallback_preference: ragFallback,
        preferred_code_language: codeLanguage,
        include_math_formulas: includeMath,
        include_visualizations: includeVisuals,
      }).unwrap();
      
      toast.success('Settings saved successfully!');
    } catch (error) {
      toast.error('Failed to save settings');
    }
  };

  return (
    <MainLayout>
      <div className="max-w-4xl animate-in fade-in duration-500 space-y-6">
        <h2 className="text-2xl font-bold text-slate-800" style={{ fontFamily: "'Playfair Display', serif" }}>
          Settings
        </h2>
        
        {/* Profile Settings */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200">
          <div className="p-6 border-b border-slate-100">
            <h3 className="text-lg font-semibold text-slate-800 mb-4">Profile</h3>
            <div className="flex items-center gap-6 mb-6">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#90AB8B] to-[#5A7863] flex items-center justify-center text-2xl font-bold text-white shadow-md border-4 border-white">
                {profile ? getInitials(profile.username) : 'U'}
              </div>
              <div>
                <button className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors">
                  Change Avatar
                </button>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">User Name</label>
                <input 
                  type="text" 
                  defaultValue={profile?.username || 'Loading...'} 
                  className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500 outline-none" 
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Email</label>
                <input 
                  type="email" 
                  defaultValue={profile?.email || 'Loading...'} 
                  className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500 outline-none" 
                />
              </div>
            </div>
          </div>
          
          {/* Learning Preferences */}
          <div className="p-6 border-b border-slate-100">
            <h3 className="text-lg font-semibold text-slate-800 mb-4">Learning Preferences</h3>
            
            <div className="space-y-6">
              {/* Learning Level */}
              <div>
                <label className="text-sm font-medium text-slate-700 mb-3 block">Learning Level</label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { value: LearningLevel.BEGINNER, label: 'Beginner' },
                    { value: LearningLevel.INTERMEDIATE, label: 'Intermediate' },
                    { value: LearningLevel.ADVANCED, label: 'Advanced' }
                  ].map((option) => (
                    <button
                      key={option.value}
                      onClick={() => setLearningLevel(option.value)}
                      className={`px-4 py-3 rounded-lg border-2 transition-all font-medium text-sm ${
                        learningLevel === option.value
                          ? 'border-sage-500 bg-sage-50 text-sage-700'
                          : 'border-slate-200 text-slate-600 hover:border-slate-300'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Explanation Style */}
              <div>
                <label className="text-sm font-medium text-slate-700 mb-3 block">Explanation Style</label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { value: ExplanationStyle.INTUITIVE, label: 'Intuitive', desc: 'Simple analogies' },
                    { value: ExplanationStyle.BALANCED, label: 'Balanced', desc: 'Mix of both' },
                    { value: ExplanationStyle.TECHNICAL, label: 'Technical', desc: 'Rigorous math' }
                  ].map((option) => (
                    <button
                      key={option.value}
                      onClick={() => setExplanationStyle(option.value)}
                      className={`px-4 py-3 rounded-lg border-2 transition-all text-left ${
                        explanationStyle === option.value
                          ? 'border-sage-500 bg-sage-50'
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className={`font-medium text-sm ${explanationStyle === option.value ? 'text-sage-700' : 'text-slate-800'}`}>
                        {option.label}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5">{option.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Learning Goal */}
              <div>
                <label className="text-sm font-medium text-slate-700 mb-3 block">Learning Goal</label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { value: LearningGoal.QUICK_REVIEW, label: 'Quick Review' },
                    { value: LearningGoal.DEEP_LEARNING, label: 'Deep Learning' },
                    { value: LearningGoal.EXAM_PREP, label: 'Exam Prep' },
                    { value: LearningGoal.RESEARCH, label: 'Research' }
                  ].map((option) => (
                    <button
                      key={option.value}
                      onClick={() => setLearningGoal(option.value)}
                      className={`px-4 py-3 rounded-lg border-2 transition-all font-medium text-sm ${
                        learningGoal === option.value
                          ? 'border-sage-500 bg-sage-50 text-sage-700'
                          : 'border-slate-200 text-slate-600 hover:border-slate-300'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* RAG Fallback Preference */}
              <div>
                <label className="text-sm font-medium text-slate-700 mb-3 block">Document-Based Answers</label>
                <p className="text-xs text-slate-500 mb-3">What should I do when your documents don&apos;t have the answer?</p>
                <div className="space-y-2">
                  {[
                    { value: RAGFallbackPreference.ALWAYS_ASK, label: 'Ask me each time', desc: 'I will offer choices' },
                    { value: RAGFallbackPreference.PREFER_GENERAL, label: 'Use AI knowledge', desc: 'Answer from general knowledge' },
                    { value: RAGFallbackPreference.STRICT_DOCUMENTS, label: 'Only my documents', desc: 'Never use general knowledge' }
                  ].map((option) => (
                    <button
                      key={option.value}
                      onClick={() => setRagFallback(option.value)}
                      className={`w-full p-3 rounded-lg border-2 transition-all text-left ${
                        ragFallback === option.value
                          ? 'border-sage-500 bg-sage-50'
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className={`font-medium text-sm ${ragFallback === option.value ? 'text-sage-700' : 'text-slate-800'}`}>
                        {option.label}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5">{option.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Additional Preferences */}
          <div className="p-6 border-b border-slate-100">
            <h3 className="text-lg font-semibold text-slate-800 mb-4">Additional Preferences</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 hover:bg-slate-50 rounded-xl transition-colors">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg text-slate-600">
                    <FileText size={18} />
                  </div>
                  <div>
                    <p className="font-medium text-slate-700">Include Math Formulas</p>
                    <p className="text-xs text-slate-500">Show LaTeX equations in explanations</p>
                  </div>
                </div>
                <button
                  onClick={() => setIncludeMath(!includeMath)}
                  className={`w-11 h-6 rounded-full relative transition-colors ${
                    includeMath ? 'bg-sage-500' : 'bg-slate-200'
                  }`}
                >
                  <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all shadow-sm ${
                    includeMath ? 'left-6' : 'left-1'
                  }`} />
                </button>
              </div>

              <div className="flex items-center justify-between p-3 hover:bg-slate-50 rounded-xl transition-colors">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg text-slate-600">
                    <BookOpen size={18} />
                  </div>
                  <div>
                    <p className="font-medium text-slate-700">Include Visualizations</p>
                    <p className="text-xs text-slate-500">Show diagrams and visual aids</p>
                  </div>
                </div>
                <button
                  onClick={() => setIncludeVisuals(!includeVisuals)}
                  className={`w-11 h-6 rounded-full relative transition-colors ${
                    includeVisuals ? 'bg-sage-500' : 'bg-slate-200'
                  }`}
                >
                  <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all shadow-sm ${
                    includeVisuals ? 'left-6' : 'left-1'
                  }`} />
                </button>
              </div>

              <div className="flex items-center justify-between p-3 hover:bg-slate-50 rounded-xl transition-colors">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg text-slate-600">
                    <Code size={18} />
                  </div>
                  <div>
                    <p className="font-medium text-slate-700">Preferred Code Language</p>
                    <p className="text-xs text-slate-500">Default language for code examples</p>
                  </div>
                </div>
                <select
                  value={codeLanguage}
                  onChange={(e) => setCodeLanguage(e.target.value)}
                  className="px-3 py-1.5 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500 outline-none"
                >
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="java">Java</option>
                  <option value="cpp">C++</option>
                </select>
              </div>
            </div>
          </div>

          {/* System Preferences */}
          <div className="p-6 border-b border-slate-100">
            <h3 className="text-lg font-semibold text-slate-800 mb-4">System</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 hover:bg-slate-50 rounded-xl transition-colors cursor-pointer">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg text-slate-600">
                    <Moon size={18} />
                  </div>
                  <div>
                    <p className="font-medium text-slate-700">Dark Mode</p>
                    <p className="text-xs text-slate-500">Coming soon</p>
                  </div>
                </div>
                <div className="w-11 h-6 bg-slate-200 rounded-full relative">
                  <div className="w-4 h-4 bg-white rounded-full absolute left-1 top-1 shadow-sm" />
                </div>
              </div>

              <div className="flex items-center justify-between p-3 hover:bg-slate-50 rounded-xl transition-colors cursor-pointer">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg text-slate-600">
                    <Shield size={18} />
                  </div>
                  <div>
                    <p className="font-medium text-slate-700">Data Privacy</p>
                    <p className="text-xs text-slate-500">Manage how your data is used</p>
                  </div>
                </div>
                <ChevronRight size={18} className="text-slate-400" />
              </div>
            </div>
          </div>

          {/* Save Button & Logout */}
          <div className="p-6 flex items-center justify-between">
            <button className="flex items-center gap-2 text-rose-600 hover:text-rose-700 font-medium text-sm">
              <LogOut size={16} />
              <span>Sign Out</span>
            </button>
            
            <button 
              onClick={handleSave}
              disabled={isSaving}
              className="px-6 py-2.5 text-white rounded-xl hover:opacity-90 disabled:opacity-50 transition-all shadow-sm font-medium"
              style={{ backgroundColor: COLORS.primary }}
            >
              {isSaving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
