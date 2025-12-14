import { useState } from 'react';
import { ArrowLeft, File, MessageSquare, Send, Sparkles, Upload } from 'lucide-react';

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

  const handleAskQuestion = () => {
    if (!question.trim()) return;

    const newQuestion: Message = {
      id: Math.random().toString(36).substring(7),
      type: 'question',
      content: question
    };

    // Simulate AI response
    const answer: Message = {
      id: Math.random().toString(36).substring(7),
      type: 'answer',
      content: `Based on the paper "${selectedPaper?.title}", here's what I found: This is a simulated response. In a real implementation, this would be powered by AI analyzing the PDF content.`
    };

    setMessages([...messages, newQuestion, answer]);
    setQuestion('');
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="px-8 py-6 flex items-center justify-between border-b border-gray-200">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-[#41337A] rounded-lg flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-[#41337A]">ResearchQ</h1>
          </div>
        </div>

        <button
          onClick={onUploadMore}
          className="flex items-center gap-2 px-4 py-2 text-[#41337A] border border-[#41337A] rounded-lg hover:bg-[#41337A]/5 transition-colors"
        >
          <Upload className="w-4 h-4" />
          Upload More
        </button>
      </header>

      <div className="flex-1 flex">
        {/* Papers Sidebar */}
        <aside className="w-80 bg-white border-r border-gray-200 p-6">
          <h3 className="mb-4">Your Papers ({papers.length})</h3>
          
          <div className="space-y-2">
            {papers.map((paper) => (
              <button
                key={paper.id}
                onClick={() => setSelectedPaper(paper)}
                className={`w-full p-4 rounded-lg text-left transition-all ${
                  selectedPaper?.id === paper.id
                    ? 'bg-[#41337A]/10 border-2 border-[#41337A]'
                    : 'bg-gray-50 border-2 border-transparent hover:bg-gray-100'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    selectedPaper?.id === paper.id ? 'bg-[#41337A]' : 'bg-white'
                  }`}>
                    <File className={`w-5 h-5 ${
                      selectedPaper?.id === paper.id ? 'text-white' : 'text-[#41337A]'
                    }`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm truncate mb-1 ${
                      selectedPaper?.id === paper.id ? 'text-[#41337A]' : 'text-gray-900'
                    }`} style={{ fontWeight: 500 }}>
                      {paper.title}
                    </p>
                    <p className="text-xs text-gray-500">
                      {paper.uploadDate.toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </aside>

        {/* Chat Area */}
        <main className="flex-1 flex flex-col">
          {selectedPaper ? (
            <>
              {/* Selected Paper Header */}
              <div className="px-8 py-6 bg-white border-b border-gray-200">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-[#41337A]/10 rounded-xl flex items-center justify-center">
                    <File className="w-6 h-6 text-[#41337A]" />
                  </div>
                  <div>
                    <h3 className="mb-1">{selectedPaper.title}</h3>
                    <p className="text-sm text-gray-500">Ask questions about this paper</p>
                  </div>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-8 py-8">
                {messages.length === 0 ? (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-center max-w-md">
                      <div className="w-16 h-16 bg-[#41337A]/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                        <MessageSquare className="w-8 h-8 text-[#41337A]" />
                      </div>
                      <h3 className="mb-2">Start asking questions</h3>
                      <p className="text-gray-500">
                        Ask anything about the methodology, findings, or conclusions in this paper
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="max-w-3xl mx-auto space-y-6">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`flex gap-4 ${
                          message.type === 'question' ? 'justify-end' : 'justify-start'
                        }`}
                      >
                        {message.type === 'answer' && (
                          <div className="w-10 h-10 bg-[#41337A] rounded-lg flex items-center justify-center flex-shrink-0">
                            <Sparkles className="w-5 h-5 text-white" />
                          </div>
                        )}
                        <div
                          className={`max-w-xl p-4 rounded-2xl ${
                            message.type === 'question'
                              ? 'bg-[#41337A] text-white'
                              : 'bg-white border border-gray-200'
                          }`}
                        >
                          <p className="text-sm leading-relaxed">{message.content}</p>
                        </div>
                        {message.type === 'question' && (
                          <div className="w-10 h-10 bg-gray-200 rounded-lg flex items-center justify-center flex-shrink-0">
                            <span className="text-sm">You</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Input Area */}
              <div className="px-8 py-6 bg-white border-t border-gray-200">
                <div className="max-w-3xl mx-auto">
                  <div className="flex gap-3">
                    <input
                      type="text"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleAskQuestion()}
                      placeholder="Ask a question about this paper..."
                      className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#41337A] focus:border-transparent"
                    />
                    <button
                      onClick={handleAskQuestion}
                      disabled={!question.trim()}
                      className="px-6 py-3 bg-[#41337A] text-white rounded-lg hover:bg-[#41337A]/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      <Send className="w-4 h-4" />
                      Ask
                    </button>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-gray-500">Select a paper to start asking questions</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
