# ResearchQ Backend - RAG Pipeline

## ✅ Status: Steps 1-5 Complete

All components of the RAG pipeline are working end-to-end.

### Components

1. **[parse_pdf.py](parse_pdf.py)** - PDF extraction with header/footer removal
2. **[chunk_text.py](chunk_text.py)** - Text chunking with overlap
3. **[embeddings.py](embeddings.py)** - Embedding generation and Pinecone storage
4. **[query.py](query.py)** - Vector DB retrieval
5. **[test_pipeline.py](test_pipeline.py)** - End-to-end integration test

---

## Setup

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX_NAME=researchq
```

### 2. Install Dependencies

```bash
pip install pypdf openai pinecone python-dotenv
```

### 3. Create Pinecone Index

- Dimensions: **1536**
- Metric: **cosine**
- Name: **researchq**

---

## Usage

### Extract and Store a Paper

```bash
# 1. Extract text from PDF
cd backend
python parse_pdf.py

# 2. Run the full pipeline (extract, chunk, embed, store)
python test_pipeline.py
```

### Query the Vector DB

```bash
python query.py
```

---

## Test Results

### ✅ All Tests Passing

```
[STEP 1] Testing PDF extraction... ✓ Extracted 11 pages
[STEP 2] Testing header removal... ✓ Cleaned 11 pages
[STEP 3] Testing chunking... ✓ Created 15 chunks
[STEP 4] Testing embedding generation... ✓ Generated 3 embeddings (dimension: 1536)
[STEP 5] Testing Pinecone storage... ✓ Stored 3 vectors in Pinecone
```

### 📊 Retrieval Quality

**Issue Found**: Only 3 chunks were stored (test mode), so retrieval is limited to chunks 0-2.

**Observations**:
- Scores range from 0.22 to 0.68 (reasonable semantic similarity)
- The same 3 chunks appear for all queries (expected, since only 3 stored)
- Chunks 0-1 are from the abstract/intro (high-level content)
- Chunk 2 is from the literature review (autonomy concepts)

**Next Steps**:
1. ✅ Store ALL 15 chunks (not just first 3)
2. Re-test retrieval to see if relevant chunks are retrieved
3. Consider increasing chunk size if content is too fragmented
4. Add page number metadata for better citations

---

## Architecture

```
PDF → Extract Text → Remove Headers → Chunk (500 tokens, 50 overlap)
                                              ↓
                                         Embed (OpenAI)
                                              ↓
                                     Store in Pinecone (with metadata)
                                              ↓
Query → Embed → Search Pinecone → Return top 5 chunks
```

---

## Files

- `parse_pdf.py` - Extracts text, removes headers/footers
- `chunk_text.py` - Tokenizes and chunks text
- `embeddings.py` - Generates embeddings, stores in Pinecone
- `query.py` - Retrieves relevant chunks
- `test_pipeline.py` - Integration test
- `paper_extracted.txt` - Extracted text output
- `test_papers/research_paper.pdf` - Sample input PDF
