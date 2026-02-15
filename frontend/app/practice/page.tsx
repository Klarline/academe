'use client';

import React, { useState } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import { BookOpen, CheckCircle, XCircle, ArrowRight, ArrowLeft, RotateCcw, Loader2, History } from 'lucide-react';
import { COLORS } from '@/lib/constants';
import { useGeneratePracticeMutation, useSavePracticeSessionMutation } from '@/store/api/practiceApi';
import { PracticeQuestion } from '@/store/api/practiceApi';
import toast from 'react-hot-toast';
import Link from 'next/link';

export default function PracticePage() {
  const [generatePractice, { isLoading }] = useGeneratePracticeMutation();
  const [savePracticeSession] = useSavePracticeSessionMutation();
  const [mode, setMode] = useState<'select' | 'quiz' | 'results'>('select');
  const [topic, setTopic] = useState('');
  const [numQuestions, setNumQuestions] = useState(5);
  const [questionTypes, setQuestionTypes] = useState<string[]>(['mcq', 'short']);
  const [questions, setQuestions] = useState<PracticeQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [userAnswers, setUserAnswers] = useState<{ [key: number]: string }>({});
  const [showAnswer, setShowAnswer] = useState(false);
  const [sessionStartTime, setSessionStartTime] = useState<Date>(new Date());

  const handleStartQuiz = async () => {
    if (!topic.trim()) {
      toast.error('Please enter a topic');
      return;
    }

    try {
      const result = await generatePractice({ 
        topic: topic.trim(),
        num_questions: numQuestions,
        question_types: questionTypes
      }).unwrap();

      if (result.questions && result.questions.length > 0) {
        setQuestions(result.questions);
        setMode('quiz');
        setCurrentIndex(0);
        setUserAnswers({});
        setShowAnswer(false);
        setSessionStartTime(new Date());  // Track start time
      } else {
        toast.error('No questions generated. Upload documents on this topic first!');
      }
    } catch (error: any) {
      const errorMsg = error?.data?.detail || error?.data?.error || 'Failed to generate quiz. Make sure you have documents uploaded!';
      toast.error(errorMsg);
    }
  };

  const handleSelectAnswer = (answer: string) => {
    setUserAnswers({ ...userAnswers, [currentIndex]: answer });
    setShowAnswer(true);
  };

  const handleNext = async () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setShowAnswer(false);
    } else {
      // Save session before showing results
      try {
        const sessionData = {
          topic: topic,
          difficulty: 'intermediate',
          questions: questions.map((q, i) => ({
            question: q.question,
            type: q.type,
            options: q.options || [],
            correct_answer: q.answer,
            user_answer: userAnswers[i] || '',
            is_correct: isCorrect(i),
            time_spent_seconds: 0,
            explanation: q.explanation || ''
          })),
          score: calculateScore().correct,
          total_questions: questions.length,
          percentage: calculateScore().percentage,
          started_at: sessionStartTime,
          completed_at: new Date(),
          duration_minutes: Math.floor((new Date().getTime() - sessionStartTime.getTime()) / 60000),
          question_types: questionTypes
        };
        
        await savePracticeSession(sessionData).unwrap();
        toast.success('Session saved to history!');
      } catch (error) {
        console.error('Failed to save session:', error);
      }
      
      setMode('results');
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setShowAnswer(false);
    }
  };

  const handleRestart = () => {
    setMode('select');
    setTopic('');
    setQuestions([]);
    setCurrentIndex(0);
    setUserAnswers({});
  };

  const isCorrect = (questionIndex: number) => {
    const q = questions[questionIndex];
    const userAns = userAnswers[questionIndex]?.toLowerCase().trim();
    const correctAns = q.answer.toLowerCase().trim();
    return userAns === correctAns || userAns?.includes(correctAns) || correctAns?.includes(userAns);
  };

  const calculateScore = () => {
    let correct = 0;
    questions.forEach((q, i) => {
      if (isCorrect(i)) correct++;
    });
    return { correct, total: questions.length, percentage: Math.round((correct / questions.length) * 100) };
  };

  const currentQuestion = questions[currentIndex];
  const score = mode === 'results' ? calculateScore() : null;

  return (
    <MainLayout>
      {/* Mode: Topic Selection */}
      {mode === 'select' && (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8">
          <div className="w-24 h-24 rounded-full flex items-center justify-center mb-6 shadow-lg" style={{ backgroundColor: `${COLORS.secondary}20`, color: COLORS.primary }}>
            <BookOpen size={40} />
          </div>
          
          <h2 className="text-3xl font-bold text-slate-800 mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>
            Practice Mode
          </h2>
          <p className="text-slate-500 max-w-md mb-8">
            Generate practice questions from your learning materials
          </p>

          <div className="w-full max-w-md space-y-4">
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !isLoading && handleStartQuiz()}
              placeholder="Enter topic (e.g., PCA, Linear Algebra)"
              className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500 outline-none text-base"
            />
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-slate-600 mb-2 block">Number of Questions</label>
                <select
                  value={numQuestions}
                  onChange={(e) => setNumQuestions(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500 outline-none"
                >
                  {[3, 5, 10, 15, 20].map(n => (
                    <option key={n} value={n}>{n} questions</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="text-xs font-medium text-slate-600 mb-2 block">Question Types</label>
                <div className="flex flex-wrap gap-2">
                  {['mcq', 'short', 'code', 'explain'].map(type => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => {
                        if (questionTypes.includes(type)) {
                          setQuestionTypes(questionTypes.filter(t => t !== type));
                        } else {
                          setQuestionTypes([...questionTypes, type]);
                        }
                      }}
                      className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                        questionTypes.includes(type)
                          ? 'bg-sage-500 text-white'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {type.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            
            <button
              onClick={handleStartQuiz}
              disabled={isLoading || !topic.trim()}
              className="w-full py-3 text-white rounded-xl font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center justify-center gap-2"
              style={{ backgroundColor: COLORS.primary }}
            >
              {isLoading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Generating Quiz...
                </>
              ) : (
                <>
                  Start Practice
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Mode: Quiz */}
      {mode === 'quiz' && currentQuestion && (
        <div className="max-w-3xl mx-auto space-y-6 py-8">
          <div className="flex items-center justify-between mb-6">
            <span className="text-sm font-medium text-slate-600">
              Question {currentIndex + 1} of {questions.length}
            </span>
            <div className="flex gap-2">
              {questions.map((_, i) => (
                <div
                  key={i}
                  className={`w-2 h-2 rounded-full transition-colors ${
                    i === currentIndex ? 'bg-sage-500 w-8' : i in userAnswers ? 'bg-sage-300' : 'bg-slate-200'
                  }`}
                />
              ))}
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
            <div className="mb-6">
              <span className="px-3 py-1 bg-sage-50 text-sage-700 text-xs font-semibold rounded-full uppercase">
                {currentQuestion.type}
              </span>
            </div>
            
            <h3 className="text-xl font-bold text-slate-800 mb-6 leading-relaxed">
              {currentQuestion.question}
            </h3>

            {/* MCQ Options */}
            {currentQuestion.type === 'mcq' && currentQuestion.options && (
              <div className="space-y-3 mb-6">
                {currentQuestion.options.map((option, i) => {
                  const isSelected = userAnswers[currentIndex] === option;
                  const isCorrectOption = option.toLowerCase().trim() === currentQuestion.answer.toLowerCase().trim();
                  
                  return (
                    <button
                      key={i}
                      onClick={() => handleSelectAnswer(option)}
                      disabled={showAnswer}
                      className={`w-full p-4 border-2 rounded-xl text-left transition-all font-medium ${
                        showAnswer
                          ? isCorrectOption
                            ? 'border-emerald-500 bg-emerald-50 text-emerald-800'
                            : isSelected
                            ? 'border-rose-500 bg-rose-50 text-rose-800'
                            : 'border-slate-200 text-slate-600'
                          : isSelected
                          ? 'border-sage-500 bg-sage-50 text-sage-800'
                          : 'border-slate-200 text-slate-700 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{option}</span>
                        {showAnswer && isCorrectOption && <CheckCircle size={20} className="text-emerald-600" />}
                        {showAnswer && isSelected && !isCorrectOption && <XCircle size={20} className="text-rose-600" />}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}

            {/* Short Answer / Code / Explain */}
            {currentQuestion.type !== 'mcq' && (
              <div className="space-y-4 mb-6">
                <textarea
                  value={userAnswers[currentIndex] || ''}
                  onChange={(e) => setUserAnswers({ ...userAnswers, [currentIndex]: e.target.value })}
                  placeholder="Type your answer here..."
                  disabled={showAnswer}
                  rows={currentQuestion.type === 'code' ? 8 : 4}
                  className={`w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500 outline-none disabled:bg-slate-50 ${
                    currentQuestion.type === 'code' ? 'font-mono text-sm' : ''
                  }`}
                />
                {!showAnswer && (
                  <button
                    onClick={() => handleSelectAnswer(userAnswers[currentIndex] || '')}
                    disabled={!userAnswers[currentIndex]?.trim()}
                    className="px-6 py-2.5 text-white rounded-xl font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    style={{ backgroundColor: COLORS.primary }}
                  >
                    Submit Answer
                  </button>
                )}
              </div>
            )}

            {/* Answer Feedback */}
            {showAnswer && (
              <div className={`p-4 rounded-xl border-2 ${
                isCorrect(currentIndex) 
                  ? 'bg-emerald-50 border-emerald-200' 
                  : 'bg-rose-50 border-rose-200'
              }`}>
                <div className="flex items-center gap-2 mb-3">
                  {isCorrect(currentIndex) ? (
                    <>
                      <CheckCircle size={20} className="text-emerald-600" />
                      <span className="font-bold text-emerald-800">Correct!</span>
                    </>
                  ) : (
                    <>
                      <XCircle size={20} className="text-rose-600" />
                      <span className="font-bold text-rose-800">Not quite right</span>
                    </>
                  )}
                </div>
                <p className="text-sm mb-2 font-medium text-slate-700">
                  <strong>Correct Answer:</strong> {currentQuestion.answer}
                </p>
                {currentQuestion.explanation && (
                  <p className="text-sm text-slate-600 leading-relaxed">
                    {currentQuestion.explanation}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex justify-between">
            <button
              onClick={handlePrevious}
              disabled={currentIndex === 0}
              className="flex items-center gap-2 px-6 py-3 border border-slate-200 rounded-xl font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              <ArrowLeft size={18} />
              Previous
            </button>

            <button
              onClick={handleNext}
              disabled={!showAnswer}
              className="flex items-center gap-2 px-6 py-3 text-white rounded-xl font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
              style={{ backgroundColor: COLORS.primary }}
            >
              {currentIndex < questions.length - 1 ? 'Next Question' : 'See Results'}
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      )}

      {/* Mode: Results */}
      {mode === 'results' && score && (
        <div className="max-w-2xl mx-auto text-center space-y-8 py-12">
          <div 
            className="w-32 h-32 rounded-full flex flex-col items-center justify-center mx-auto shadow-lg border-4"
            style={{ 
              backgroundColor: score.percentage >= 70 ? '#D4EDDA' : score.percentage >= 50 ? '#FFF3CD' : '#F8D7DA',
              borderColor: score.percentage >= 70 ? '#C3E6CB' : score.percentage >= 50 ? '#FFEAA7' : '#F5C6CB',
              color: score.percentage >= 70 ? '#155724' : score.percentage >= 50 ? '#856404' : '#721C24'
            }}
          >
            <span className="text-5xl font-bold">{score.percentage}</span>
            <span className="text-sm font-medium">%</span>
          </div>

          <div>
            <h2 className="text-3xl font-bold text-slate-800 mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>
              {score.percentage >= 90 ? 'Outstanding!' : score.percentage >= 70 ? 'Well Done!' : score.percentage >= 50 ? 'Good Effort!' : 'Keep Practicing!'}
            </h2>
            
            <p className="text-lg text-slate-600">
              You answered <strong className="text-sage-600">{score.correct}</strong> out of <strong>{score.total}</strong> questions correctly
            </p>
          </div>

          {/* Review Summary */}
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 text-left">
            <h3 className="font-bold text-slate-800 mb-4">Question Review</h3>
            <div className="space-y-2">
              {questions.map((q, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50">
                  <span className="text-sm text-slate-700">Question {i + 1}</span>
                  {isCorrect(i) ? (
                    <CheckCircle size={18} className="text-emerald-600" />
                  ) : (
                    <XCircle size={18} className="text-rose-600" />
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex gap-4 justify-center">
            <button
              onClick={handleRestart}
              className="px-8 py-3 text-white rounded-xl font-semibold hover:opacity-90 transition-all shadow-sm flex items-center gap-2"
              style={{ backgroundColor: COLORS.primary }}
            >
              <RotateCcw size={18} />
              Try Another Topic
            </button>
            
            <Link
              href="/practice/history"
              className="px-8 py-3 border-2 border-sage-500 text-sage-700 rounded-xl font-semibold hover:bg-sage-50 transition-all flex items-center gap-2"
            >
              <History size={18} />
              View History
            </Link>
          </div>
        </div>
      )}
    </MainLayout>
  );
}
