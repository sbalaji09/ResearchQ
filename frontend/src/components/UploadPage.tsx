import { useState, useCallback } from 'react';
import { Upload, File, X, ArrowLeft, Sparkles, Check } from 'lucide-react';
import { uploadPaper } from '@/api';

interface UploadPageProps {
  onUpload: (files: File[]) => void;
  onBack: () => void;
}

export function UploadPage({ onUpload, onBack }: UploadPageProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

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

  const handleUpload = async () => {
    if (selectedFiles.length === 0 || isUploading) return;
  
    setIsUploading(true);
    setError(null);
    setSuccess(false);
  
    try {
      // Upload each file
      for (const file of selectedFiles) {
        await uploadPaper(file);   // <-- calls backend /upload
      }
  
      setSuccess(true);
  
      // Notify parent so it can navigate to the Papers view
      onUpload(selectedFiles);
  
      // Clear selected files
      setSelectedFiles([]);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Upload failed. Please try again.";
      setError(msg);
    } finally {
      setIsUploading(false);
    }
  };
  

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50">
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
        </div>
      </header>

      {/* Main Content */}
      <main className="px-6 md:px-12 py-16 max-w-5xl mx-auto">
        <div className="mb-12 text-center">
          <h2 
            className="mb-3"
            style={{ fontSize: '2.5rem', fontWeight: 700, letterSpacing: '-0.02em' }}
          >
            Upload Your Research Papers
          </h2>
          <p className="text-gray-600 text-lg">
            Add PDF files to start asking questions about your research
          </p>
        </div>

        {/* Upload Area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`relative border-2 border-dashed rounded-3xl p-16 text-center transition-all duration-300 ${
            isDragging
              ? 'border-[#41337A] bg-gradient-to-br from-[#41337A]/5 to-purple-50/50 scale-[1.01]'
              : 'border-gray-300 hover:border-gray-400 bg-white'
          }`}
        >
          <div className="max-w-md mx-auto">
            <div className={`relative w-20 h-20 mx-auto mb-6 transition-all duration-300 ${
              isDragging ? 'scale-110' : ''
            }`}>
              <div className={`absolute inset-0 rounded-3xl transition-all duration-300 ${
                isDragging 
                  ? 'bg-gradient-to-br from-[#41337A] to-[#5a4a9f] shadow-2xl shadow-[#41337A]/40' 
                  : 'bg-gradient-to-br from-gray-100 to-gray-200'
              }`}></div>
              <div className="relative w-full h-full flex items-center justify-center">
                <Upload className={`w-9 h-9 transition-colors duration-300 ${
                  isDragging ? 'text-white' : 'text-gray-400'
                }`} strokeWidth={2} />
              </div>
            </div>

            <h3 
              className="mb-2"
              style={{ fontSize: '1.25rem', fontWeight: 600 }}
            >
              {isDragging ? 'Drop your files here' : 'Drag & drop PDF files'}
            </h3>
            <p className="text-gray-500 mb-6">or click below to browse</p>

            <label className="inline-flex items-center gap-2 bg-gradient-to-r from-[#41337A] to-[#5a4a9f] text-white px-6 py-3 rounded-xl hover:shadow-xl hover:shadow-[#41337A]/30 transition-all duration-300 hover:-translate-y-0.5 cursor-pointer">
              <File className="w-4 h-4" />
              <span style={{ fontWeight: 500 }}>Choose Files</span>
              <input
                type="file"
                multiple
                accept=".pdf"
                onChange={handleFileSelect}
                className="hidden"
              />
            </label>

            <p className="text-sm text-gray-400 mt-6">Supports PDF files up to 50MB</p>
          </div>
        </div>

        {/* Selected Files */}
        {selectedFiles.length > 0 && (
          <div className="mt-12 bg-white rounded-2xl border border-gray-200 p-8 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h3 style={{ fontSize: '1.25rem', fontWeight: 600 }}>
                Selected Files ({selectedFiles.length})
              </h3>
              <div className="flex items-center gap-2 text-sm text-green-600">
                <Check className="w-4 h-4" />
                <span>Ready to upload</span>
              </div>
            </div>
            
            <div className="space-y-3 mb-8">
              {selectedFiles.map((file, index) => (
                <div
                  key={index}
                  className="group flex items-center justify-between p-4 bg-gradient-to-br from-gray-50 to-white rounded-xl border border-gray-200 hover:border-[#41337A]/20 hover:shadow-md transition-all duration-300"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-gradient-to-br from-[#41337A]/10 to-purple-100/50 rounded-xl flex items-center justify-center border border-[#41337A]/10">
                      <File className="w-6 h-6 text-[#41337A]" />
                    </div>
                    <div>
                      <p className="text-sm mb-1" style={{ fontWeight: 500 }}>
                        {file.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="p-2 hover:bg-red-50 rounded-lg transition-all duration-300 opacity-0 group-hover:opacity-100"
                  >
                    <X className="w-4 h-4 text-red-500" />
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={handleUpload}
              className="w-full bg-gradient-to-r from-[#41337A] to-[#5a4a9f] text-white px-6 py-4 rounded-xl hover:shadow-2xl hover:shadow-[#41337A]/30 transition-all duration-300 hover:-translate-y-0.5 flex items-center justify-center gap-2"
              style={{ fontWeight: 600 }}
            >
              <Upload className="w-5 h-5" />
              Upload {selectedFiles.length} {selectedFiles.length === 1 ? 'Paper' : 'Papers'}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
