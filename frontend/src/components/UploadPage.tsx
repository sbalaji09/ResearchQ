import { useState, useCallback, useEffect } from 'react';
import { Upload, File, X, ArrowLeft, Sparkles, Loader2, AlertCircle } from 'lucide-react';
import { uploadPaper } from '@/api';

interface UploadPageProps {
  onUpload: (files: File[], sessionId?: string) => void;
  onBack: () => void;
  sessionId: string | null;
}

export function UploadPage({ onUpload, onBack, sessionId }: UploadPageProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Create object URL for PDF preview
  useEffect(() => {
    if (selectedFile) {
      const url = URL.createObjectURL(selectedFile);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setPreviewUrl(null);
    }
  }, [selectedFile]);

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

    if (files.length > 0) {
      setSelectedFile(files[0]);
      setError(null);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setError(null);
    }
  }, []);

  const removeFile = () => {
    setSelectedFile(null);
    setError(null);
  };

  const handleUpload = async () => {
    if (!selectedFile || isUploading) return;

    setIsUploading(true);
    setError(null);

    try {
      const response = await uploadPaper(selectedFile, sessionId || undefined);
      // Pass the session_id back to parent so it can track for cleanup
      onUpload([selectedFile], response.session_id);
      setSelectedFile(null);
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
            Upload Your Research Paper
          </h2>
          <p className="text-gray-600 text-lg">
            Add a PDF file to start asking questions about your research
          </p>
        </div>

        {/* Upload Area / Preview Area */}
        <div className="relative border-2 rounded-3xl transition-all duration-300 bg-white overflow-hidden"
          style={{ borderStyle: selectedFile ? 'solid' : 'dashed' }}
        >
          {!selectedFile ? (
            // Empty state - Upload dropzone
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`p-16 text-center transition-all duration-300 ${
                isDragging
                  ? 'border-[#41337A] bg-gradient-to-br from-[#41337A]/5 to-purple-50/50 scale-[1.01]'
                  : 'border-gray-300 hover:border-gray-400'
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
                  {isDragging ? 'Drop your file here' : 'Drag & drop a PDF file'}
                </h3>
                <p className="text-gray-500 mb-6">or click below to browse</p>

                <label className="inline-flex items-center gap-2 bg-gradient-to-r from-[#41337A] to-[#5a4a9f] text-white px-6 py-3 rounded-xl hover:shadow-xl hover:shadow-[#41337A]/30 transition-all duration-300 hover:-translate-y-0.5 cursor-pointer">
                  <File className="w-4 h-4" />
                  <span style={{ fontWeight: 500 }}>Choose File</span>
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </label>

                <p className="text-sm text-gray-400 mt-6">Supports PDF files up to 50MB</p>
              </div>
            </div>
          ) : (
            // File selected - Show preview
            <div className="p-6">
              {/* File header with name and remove button */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-[#41337A]/10 to-purple-100/50 rounded-xl flex items-center justify-center border border-[#41337A]/10">
                    <File className="w-5 h-5 text-[#41337A]" />
                  </div>
                  <div>
                    <p className="text-sm" style={{ fontWeight: 600 }}>
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                <button
                  onClick={removeFile}
                  className="p-2 hover:bg-red-50 rounded-lg transition-all duration-300"
                  title="Remove file"
                >
                  <X className="w-5 h-5 text-red-500" />
                </button>
              </div>

              {/* PDF Preview */}
              <div className="rounded-2xl overflow-hidden border border-gray-200 bg-gray-100 mb-6">
                {previewUrl && (
                  <object
                    data={`${previewUrl}#page=1&view=FitH&toolbar=0&navpanes=0&scrollbar=0`}
                    type="application/pdf"
                    className="w-full"
                    style={{ height: '400px' }}
                  >
                    <div className="flex items-center justify-center h-64 text-gray-500">
                      <div className="text-center">
                        <File className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                        <p>PDF preview not available</p>
                        <p className="text-sm text-gray-400 mt-1">{selectedFile.name}</p>
                      </div>
                    </div>
                  </object>
                )}
              </div>

              {/* Error message */}
              {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-red-700">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  <span className="text-sm">{error}</span>
                </div>
              )}

              {/* Upload button */}
              <button
                onClick={handleUpload}
                disabled={isUploading}
                className={`w-full bg-gradient-to-r from-[#41337A] to-[#5a4a9f] text-white px-6 py-4 rounded-xl transition-all duration-300 flex items-center justify-center gap-2 ${
                  isUploading
                    ? 'opacity-70 cursor-not-allowed'
                    : 'hover:shadow-2xl hover:shadow-[#41337A]/30 hover:-translate-y-0.5'
                }`}
                style={{ fontWeight: 600 }}
              >
                {isUploading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    Upload Paper
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
