# base exception for ResearchQ
class ResearchQError(Exception):
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

# raised when PDF parsing fails
class PDFParsingError(ResearchQError):
    def __init__(self, message: str, pdf_name: str = None):
        self.pdf_name = pdf_name
        super().__init__(message, "PDF_PARSING_ERROR")

# raised when no text could be extracted from PDF
class NoTextExtractedError(PDFParsingError):
    def __init__(self, pdf_name: str):
        super().__init__(
            f"Could not extract any text from '{pdf_name}'. The PDF may be corrupted or image-only.",
            pdf_name
        )
    
# raised when retrieval fails
class RetrievalError(ResearchQError):
    def __init__(self, message: str):
        super().__init__(message, "RETRIEVAL_ERROR")

# raised when no relevant chunks are found
class NoRelevantChunksError(RetrievalError):
    def __init__(self, question: str, threshold: float = 0.3):
        self.question = question
        self.threshold = threshold
        super().__init__(
            f"No relevant information found for your question. Try rephrasing or uploading more relevant documents."
        )

# raised when chunks have low relevance scores
class LowRelevanceError(RetrievalError):
    def __init__(self, best_score: float, threshold: float = 0.3):
        self.best_score = best_score
        super().__init__(
            f"The available documents may not contain information directly relevant to your question (confidence: {best_score:.0%})."
        )

# raised when LLM generation fails
class GenerationError(ResearchQError):
    def __init__(self, message: str):
        super().__init__(message, "GENERATION_ERROR")

# raised when potential hallucination is detected
class HallucinationWarning(ResearchQError):
    def __init__(self, message: str):
        super().__init__(message, "HALLUCINATION_WARNING")