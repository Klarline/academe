'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, ArrowLeft, Check } from 'lucide-react';
import { COLORS, LearningLevel, LearningGoal, ExplanationStyle, RAGFallbackPreference } from '@/lib/constants';
import { useCompleteOnboardingMutation } from '@/store/api/userApi';
import toast from 'react-hot-toast';

export default function OnboardingPage() {
  const router = useRouter();
  const [completeOnboarding, { isLoading }] = useCompleteOnboardingMutation();
  const [currentStep, setCurrentStep] = useState(1);
  const [preferences, setPreferences] = useState({
    learning_level: LearningLevel.INTERMEDIATE,
    learning_goal: LearningGoal.DEEP_LEARNING,
    explanation_style: ExplanationStyle.BALANCED,
    rag_fallback_preference: RAGFallbackPreference.ALWAYS_ASK,
    preferred_code_language: 'python',
    include_math_formulas: true,
    include_visualizations: true,
  });

  const totalSteps = 5;
  const handleNext = () => currentStep < totalSteps && setCurrentStep(currentStep + 1);
  const handleBack = () => currentStep > 1 && setCurrentStep(currentStep - 1);

  const handleComplete = async () => {
    try {
      await completeOnboarding(preferences).unwrap();
      toast.success('Welcome to Academe! 🎉');
      router.push('/dashboard');
    } catch (error) {
      toast.error('Failed to save preferences');
    }
  };

  return (
    <div className="w-full max-w-2xl">
      <div className="text-center mb-8">
        <div 
          className="w-16 h-16 rounded-2xl flex items-center justify-center text-white font-bold text-3xl shadow-lg mx-auto mb-4"
          style={{ backgroundColor: COLORS.primary, fontFamily: "'Playfair Display', serif" }}
        >
          à
        </div>
        <h1 className="text-3xl font-bold text-slate-800" style={{ fontFamily: "'Playfair Display', serif" }}>
          Let&apos;s Personalize Your Experience
        </h1>
        <p className="text-slate-600 mt-2">Step {currentStep} of {totalSteps}</p>
      </div>

      <div className="flex justify-center gap-2 mb-8">
        {[1, 2, 3, 4, 5].map((step) => (
          <div
            key={step}
            className={`h-2 rounded-full transition-all ${step === currentStep ? 'w-12' : 'w-8'}`}
            style={{ backgroundColor: step <= currentStep ? COLORS.primary : '#E2E8F0' }}
          />
        ))}
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 min-h-[400px]">
        {currentStep === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">What&apos;s your current learning level?</h2>
              <p className="text-slate-600 text-sm">This helps us tailor explanations to your knowledge.</p>
            </div>
            
            <div className="space-y-3">
              {[
                { value: LearningLevel.BEGINNER, label: 'Beginner', desc: 'New to ML concepts, need foundational explanations' },
                { value: LearningLevel.INTERMEDIATE, label: 'Intermediate', desc: 'Familiar with basics, ready for deeper concepts' },
                { value: LearningLevel.ADVANCED, label: 'Advanced', desc: 'Strong understanding, can handle complex theory' }
              ].map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setPreferences({ ...preferences, learning_level: option.value })}
                  className={`w-full p-4 border-2 rounded-xl text-left transition-all ${
                    preferences.learning_level === option.value
                      ? 'border-sage-500 bg-sage-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className={`font-semibold ${preferences.learning_level === option.value ? 'text-sage-700' : 'text-slate-800'}`}>
                    {option.label}
                  </div>
                  <div className="text-sm text-slate-500 mt-1">{option.desc}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {currentStep === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">What&apos;s your primary learning goal?</h2>
              <p className="text-slate-600 text-sm">This guides content depth and focus.</p>
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              {[
                { value: LearningGoal.QUICK_REVIEW, label: 'Quick Review', desc: 'Brief refresher' },
                { value: LearningGoal.DEEP_LEARNING, label: 'Deep Learning', desc: 'Thorough understanding' },
                { value: LearningGoal.EXAM_PREP, label: 'Exam Prep', desc: 'Test preparation' },
                { value: LearningGoal.RESEARCH, label: 'Research', desc: 'In-depth exploration' }
              ].map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setPreferences({ ...preferences, learning_goal: option.value })}
                  className={`p-4 border-2 rounded-xl text-left transition-all ${
                    preferences.learning_goal === option.value
                      ? 'border-sage-500 bg-sage-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className={`font-semibold ${preferences.learning_goal === option.value ? 'text-sage-700' : 'text-slate-800'}`}>
                    {option.label}
                  </div>
                  <div className="text-sm text-slate-500 mt-1">{option.desc}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {currentStep === 3 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">How do you prefer explanations?</h2>
              <p className="text-slate-600 text-sm">Choose your preferred approach to learning.</p>
            </div>
            
            <div className="space-y-3">
              {[
                { value: ExplanationStyle.INTUITIVE, label: 'Intuitive', desc: 'Simple analogies and everyday examples' },
                { value: ExplanationStyle.BALANCED, label: 'Balanced', desc: 'Mix of intuition and technical details' },
                { value: ExplanationStyle.TECHNICAL, label: 'Technical', desc: 'Rigorous mathematical explanations' }
              ].map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setPreferences({ ...preferences, explanation_style: option.value })}
                  className={`w-full p-4 border-2 rounded-xl text-left transition-all ${
                    preferences.explanation_style === option.value
                      ? 'border-sage-500 bg-sage-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className={`font-semibold ${preferences.explanation_style === option.value ? 'text-sage-700' : 'text-slate-800'}`}>
                    {option.label}
                  </div>
                  <div className="text-sm text-slate-500 mt-1">{option.desc}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {currentStep === 4 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">Document-Based Learning</h2>
              <p className="text-slate-600 text-sm">What should I do when your documents don&apos;t have an answer?</p>
            </div>
            
            <div className="space-y-3">
              {[
                { value: RAGFallbackPreference.ALWAYS_ASK, label: 'Ask me each time', desc: 'Offer choices when docs don\'t help' },
                { value: RAGFallbackPreference.PREFER_GENERAL, label: 'Use general knowledge', desc: 'Answer from AI when docs don\'t help' },
                { value: RAGFallbackPreference.STRICT_DOCUMENTS, label: 'Only my documents', desc: 'Never use general knowledge' }
              ].map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setPreferences({ ...preferences, rag_fallback_preference: option.value })}
                  className={`w-full p-4 border-2 rounded-xl text-left transition-all ${
                    preferences.rag_fallback_preference === option.value
                      ? 'border-sage-500 bg-sage-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className={`font-semibold ${preferences.rag_fallback_preference === option.value ? 'text-sage-700' : 'text-slate-800'}`}>
                    {option.label}
                  </div>
                  <div className="text-sm text-slate-500 mt-1">{option.desc}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {currentStep === 5 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">Additional Preferences</h2>
              <p className="text-slate-600 text-sm">Fine-tune your learning experience.</p>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 border border-slate-200 rounded-xl">
                <div>
                  <p className="font-medium text-slate-700">Include Math Formulas</p>
                  <p className="text-xs text-slate-500">Show LaTeX equations in explanations</p>
                </div>
                <button
                  type="button"
                  onClick={() => setPreferences({ ...preferences, include_math_formulas: !preferences.include_math_formulas })}
                  className={`w-11 h-6 rounded-full relative transition-colors ${
                    preferences.include_math_formulas ? 'bg-sage-500' : 'bg-slate-200'
                  }`}
                >
                  <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all shadow-sm ${
                    preferences.include_math_formulas ? 'left-6' : 'left-1'
                  }`} />
                </button>
              </div>

              <div className="flex items-center justify-between p-4 border border-slate-200 rounded-xl">
                <div>
                  <p className="font-medium text-slate-700">Include Visualizations</p>
                  <p className="text-xs text-slate-500">Show diagrams and visual aids</p>
                </div>
                <button
                  type="button"
                  onClick={() => setPreferences({ ...preferences, include_visualizations: !preferences.include_visualizations })}
                  className={`w-11 h-6 rounded-full relative transition-colors ${
                    preferences.include_visualizations ? 'bg-sage-500' : 'bg-slate-200'
                  }`}
                >
                  <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all shadow-sm ${
                    preferences.include_visualizations ? 'left-6' : 'left-1'
                  }`} />
                </button>
              </div>

              <div className="p-4 border border-slate-200 rounded-xl">
                <label className="text-sm font-medium text-slate-700 mb-2 block">Preferred Code Language</label>
                <select
                  value={preferences.preferred_code_language}
                  onChange={(e) => setPreferences({ ...preferences, preferred_code_language: e.target.value })}
                  className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500 outline-none"
                >
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="java">Java</option>
                  <option value="cpp">C++</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-between mt-8">
        <button
          type="button"
          onClick={handleBack}
          disabled={currentStep === 1}
          className="flex items-center gap-2 px-6 py-3 border border-slate-200 rounded-xl font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <ArrowLeft size={18} />
          Back
        </button>

        {currentStep < totalSteps ? (
          <button
            type="button"
            onClick={handleNext}
            className="flex items-center gap-2 px-6 py-3 text-white rounded-xl font-semibold hover:opacity-90 transition-all shadow-sm"
            style={{ backgroundColor: COLORS.primary }}
          >
            Next
            <ArrowRight size={18} />
          </button>
        ) : (
          <button
            type="button"
            onClick={handleComplete}
            disabled={isLoading}
            className="flex items-center gap-2 px-6 py-3 text-white rounded-xl font-semibold hover:opacity-90 disabled:opacity-50 transition-all shadow-sm"
            style={{ backgroundColor: COLORS.primary }}
          >
            {isLoading ? 'Saving...' : 'Complete'}
            <Check size={18} />
          </button>
        )}
      </div>
    </div>
  );
}
