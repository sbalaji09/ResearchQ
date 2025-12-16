import { useState } from 'react';
import { ArrowLeft, File, MessageSquare, Send, Sparkles, Upload, Zap, Loader2 } from 'lucide-react';
import { askQuestion } from '@/api';

interface Paper {
  id: string;
  title: string;
  file: File;
  uploadDate: Date;
}

interface PapersViewProps {
  papers: Paper[];
  onBack: () => void;
  onUploadMore: () => void;
}

interface Message {
  id: string;
  type: 'question' | 'answer';
  content: string;
}

export function PapersView({ papers, onBack, onUploadMore }: PapersViewProps) {
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(papers[0] || null);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAskQuestion = async () => {
    if (!question.trim() || !selectedPaper || isAsking) return;
  
    setError(null);
  
    const newQuestion: Message = {
      id: Math.random().toString(36).substring(7),
      type: "question",
      content: question.trim(),
    };
  
    // Add the user's question to chat
    setMessages(prev => [...prev, newQuestion]);
    setQuestion("");
    setIsAsking(true);
  
    try {
      // Call backend API correctly
      const answerText = await askQuestion(newQuestion.content);
  
      const answer: Message = {
        id: Math.random().toString(36).substring(7),
        type: "answer",
        content: answerText,
      };
  
      // Add answer to chat
      setMessages(prev => [...prev, answer]);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Something went wrong while asking the question.";
      setError(msg);
    } finally {
      setIsAsking(false);
    }
  };  
  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50 flex flex-col">
      {/* Header */}
      <header className="px-6 md:px-12 py-6 border-b border-gray-200 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 rounded-xl transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-[#41337A] to-[#5a4a9f] rounded-xl flex items-center justify-center shadow-lg shadow-[#41337A]/20">
                <Sparkles className="w-5 h-5 text-white" strokeWidth={2.5} />
              </div>
              <span className="text-xl" style={{ fontWeight: 600, letterSpacing: '-0.02em' }}>ResearchQ</span>
            </div>
          </div>

          <button
            onClick={onUploadMore}
            className="flex items-center gap-2 px-4 py-2 text-[#41337A] bg-[#41337A]/5 border border-[#41337A]/20 rounded-xl hover:bg-[#41337A]/10 transition-all duration-300"
            style={{ fontWeight: 500 }}
          >
            <Upload className="w-4 h-4" />
            Upload More
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Papers Sidebar */}
        <aside className="w-96 bg-white border-r border-gray-200 flex flex-col">
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <h3 style={{ fontWeight: 600 }}>Your Library</h3>
              <span className="px-3 py-1 bg-[#41337A]/10 text-[#41337A] rounded-full text-xs" style={{ fontWeight: 600 }}>
                {papers.length}
              </span>
            </div>
            <p className="text-sm text-gray-500">Select a paper to start asking questions</p>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {papers.map((paper) => (
              <button
                key={paper.id}
                onClick={() => setSelectedPaper(paper)}
                className={`w-full p-4 rounded-xl text-left transition-all duration-300 ${
                  selectedPaper?.id === paper.id
                    ? 'bg-gradient-to-br from-[#41337A] to-[#5a4a9f] shadow-xl shadow-[#41337A]/20 scale-[1.02]'
                    : 'bg-gray-50 hover:bg-gray-100 border border-gray-200'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-300 ${
                    selectedPaper?.id === paper.id 
                      ? 'bg-white/20' 
                      : 'bg-white border border-gray-200'
                  }`}>
                    <File className={`w-5 h-5 ${
                      selectedPaper?.id === paper.id ? 'text-white' : 'text-[#41337A]'
                    }`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p 
                      className={`text-sm truncate mb-1 ${
                        selectedPaper?.id === paper.id ? 'text-white' : 'text-gray-900'
                      }`} 
                      style={{ fontWeight: 500 }}
                    >
                      {paper.title}
                    </p>
                    <p className={`text-xs ${
                      selectedPaper?.id === paper.id ? 'text-white/80' : 'text-gray-500'
                    }`}>
                      {paper.uploadDate.toLocaleDateString('en-US', { 
                        month: 'short', 
                        day: 'numeric',
                        year: 'numeric'
                      })}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </aside>

        {/* Chat Area */}
        <main className="flex-1 flex flex-col bg-gradient-to-b from-gray-50/50 to-white">
          {selectedPaper ? (
            <>
              {/* Selected Paper Header */}
              <div className="px-8 py-6 bg-white border-b border-gray-200">
                <div className="max-w-4xl mx-auto">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 bg-gradient-to-br from-[#41337A]/10 to-purple-100/50 rounded-2xl flex items-center justify-center border border-[#41337A]/20">
                      <File className="w-7 h-7 text-[#41337A]" />
                    </div>
                    <div className="flex-1">
                      <h3 className="mb-1" style={{ fontWeight: 600 }}>
                        {selectedPaper.title}
                      </h3>
                      <p className="text-sm text-gray-500">
                        Ask questions about methodology, findings, or anything else
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-8 py-8">
                {messages.length === 0 ? (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-center max-w-xl">
                      <div className="relative w-20 h-20 mx-auto mb-6">
                        <div className="absolute inset-0 bg-gradient-to-br from-[#41337A] to-[#5a4a9f] rounded-3xl shadow-2xl shadow-[#41337A]/30"></div>
                        <div className="relative w-full h-full flex items-center justify-center">
                          <MessageSquare className="w-9 h-9 text-white" strokeWidth={2} />
                        </div>
                      </div>
                      <h3 
                        className="mb-3"
                        style={{ fontSize: '1.5rem', fontWeight: 600 }}
                      >
                        Ready to explore this paper
                      </h3>
                      <p className="text-gray-600 mb-8 leading-relaxed">
                        Start a conversation with AI about your research. Ask about methodology, 
                        key findings, limitations, or request summaries.
                      </p>
                      
                      {/* Suggested Questions */}
                      <div className="space-y-2">
                        <p className="text-sm text-gray-500 mb-3">Suggested questions:</p>
                        {[
                          "What is the main hypothesis of this paper?",
                          "Summarize the methodology used",
                          "What are the key findings?"
                        ].map((suggestion, idx) => (
                          <button
                            key={idx}
                            onClick={() => setQuestion(suggestion)}
                            className="block w-full text-left px-4 py-3 bg-white border border-gray-200 rounded-xl hover:border-[#41337A]/30 hover:bg-[#41337A]/5 transition-all duration-300 text-sm text-gray-700"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="max-w-4xl mx-auto space-y-6">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`flex gap-4 ${
                          message.type === 'question' ? 'justify-end' : 'justify-start'
                        }`}
                      >
                        {message.type === 'answer' && (
                          <div className="w-11 h-11 bg-gradient-to-br from-[#41337A] to-[#5a4a9f] rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-[#41337A]/20">
                            <Sparkles className="w-5 h-5 text-white" strokeWidth={2.5} />
                          </div>
                        )}
                        <div
                          className={`max-w-2xl p-5 rounded-2xl ${
                            message.type === 'question'
                              ? 'bg-gradient-to-br from-[#41337A] to-[#5a4a9f] text-white shadow-lg shadow-[#41337A]/20'
                              : 'bg-white border border-gray-200 shadow-sm'
                          }`}
                        >
                          <p className="leading-relaxed">{message.content}</p>
                        </div>
                        {message.type === 'question' && (
                          <div className="w-11 h-11 bg-gradient-to-br from-gray-100 to-gray-200 rounded-xl flex items-center justify-center flex-shrink-0">
                            <span className="text-sm" style={{ fontWeight: 500 }}>You</span>
                          </div>
                        )}
                      </div>
                    ))}

                    {/* Thinking animation */}
                    {isAsking && (
                      <div className="flex gap-4 justify-start">
                        <div className="w-11 h-11 bg-gradient-to-br from-[#41337A] to-[#5a4a9f] rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-[#41337A]/20">
                          <Loader2 className="w-5 h-5 text-white animate-spin" />
                        </div>
                        <div className="max-w-2xl p-5 rounded-2xl bg-white border border-gray-200 shadow-sm">
                          <div className="flex items-center gap-2">
                            <div className="flex gap-1">
                              <span className="w-2 h-2 bg-[#41337A] rounded-full animate-pulse" style={{ animationDelay: '0ms' }}></span>
                              <span className="w-2 h-2 bg-[#41337A] rounded-full animate-pulse" style={{ animationDelay: '150ms' }}></span>
                              <span className="w-2 h-2 bg-[#41337A] rounded-full animate-pulse" style={{ animationDelay: '300ms' }}></span>
                            </div>
                            <span className="text-gray-500 text-sm">Thinking...</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Input Area */}
              <div className="px-8 py-6 bg-white border-t border-gray-200">
                <div className="max-w-4xl mx-auto">
                  <div className="flex gap-3">
                    <div className="flex-1 relative">
                      <input
                        type="text"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAskQuestion()}
                        placeholder="Ask a question about this paper..."
                        className="w-full px-5 py-4 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#41337A] focus:border-transparent transition-all duration-300"
                      />
                      <Zap className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    </div>
                    <button
                      onClick={handleAskQuestion}
                      disabled={!question.trim() || isAsking}
                      className="px-6 py-4 bg-gradient-to-r from-[#41337A] to-[#5a4a9f] text-white rounded-xl hover:shadow-xl hover:shadow-[#41337A]/30 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none flex items-center gap-2"
                      style={{ fontWeight: 500 }}
                    >
                      {isAsking ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Thinking
                        </>
                      ) : (
                        <>
                          <Send className="w-4 h-4" />
                          Send
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <File className="w-8 h-8 text-gray-400" />
                </div>
                <p className="text-gray-500">Select a paper from your library to begin</p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
