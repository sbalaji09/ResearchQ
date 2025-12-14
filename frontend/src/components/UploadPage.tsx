import { useState, useCallback } from 'react';
import { Upload, File, X, ArrowLeft, Sparkles } from 'lucide-react';

interface UploadPageProps {
  onUpload: (files: File[]) => void;
  onBack: () => void;
}

export function UploadPage({ onUpload, onBack }: UploadPageProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files).filter(
      file => file.type === 'application/pdf'
    );
    
    setSelectedFiles(prev => [...prev, ...files]);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      setSelectedFiles(prev => [...prev, ...files]);
    }
  }, []);

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = () => {
    if (selectedFiles.length > 0) {
      onUpload(selectedFiles);
    }
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
      </header>

      {/* Main Content */}
      <main className="flex-1 px-8 py-12 max-w-4xl mx-auto w-full">
        <div className="mb-8">
          <h2 className="mb-2">Upload Research Papers</h2>
          <p className="text-gray-600">
            Upload one or more PDF files to start asking questions
          </p>
        </div>

        {/* Upload Area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-2xl p-16 text-center transition-all ${
            isDragging
              ? 'border-[#41337A] bg-[#41337A]/5 scale-[1.02]'
              : 'border-gray-300 hover:border-gray-400'
          }`}
        >
          <div className="max-w-md mx-auto">
            <div className={`w-16 h-16 mx-auto mb-6 rounded-2xl flex items-center justify-center transition-colors ${
              isDragging ? 'bg-[#41337A] scale-110' : 'bg-gray-100'
            }`}>
              <Upload className={`w-8 h-8 transition-colors ${
                isDragging ? 'text-white' : 'text-gray-400'
              }`} />
            </div>

            <h3 className="mb-3">
              {isDragging ? 'Drop files here' : 'Drag & drop your files here'}
            </h3>
            <p className="text-gray-500 mb-6">or</p>

            <label className="inline-flex items-center gap-2 bg-[#41337A] text-white px-6 py-3 rounded-lg hover:bg-[#41337A]/90 transition-colors cursor-pointer shadow-sm">
              <File className="w-4 h-4" />
              Browse Files
              <input
                type="file"
                multiple
                accept=".pdf"
                onChange={handleFileSelect}
                className="hidden"
              />
            </label>

            <p className="text-sm text-gray-400 mt-4">PDF files only</p>
          </div>
        </div>

        {/* Selected Files */}
        {selectedFiles.length > 0 && (
          <div className="mt-8 bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="mb-4">Selected Files ({selectedFiles.length})</h3>
            
            <div className="space-y-2 mb-6">
              {selectedFiles.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg group hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center border border-gray-200">
                      <File className="w-5 h-5 text-[#41337A]" />
                    </div>
                    <div>
                      <p className="text-sm">{file.name}</p>
                      <p className="text-xs text-gray-500">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="p-2 hover:bg-white rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <X className="w-4 h-4 text-gray-400" />
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={handleUpload}
              className="w-full bg-[#41337A] text-white px-6 py-3 rounded-lg hover:bg-[#41337A]/90 transition-colors shadow-sm"
            >
              Upload {selectedFiles.length} {selectedFiles.length === 1 ? 'Paper' : 'Papers'}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
