# How ResearchQ Works - Complete Explanation

## 🎯 What Is This Project?

**ResearchQ** is a RAG (Retrieval-Augmented Generation) system that allows users to:
1. Upload multiple research papers (PDFs)
2. Ask questions about them
3. Get answers based on the actual content of the papers

Think of it as "ChatGPT for your research papers" - instead of searching through PDFs manually, you ask questions in natural language and get relevant excerpts from the papers.

---

## 🧠 How RAG Works (The Big Picture)

```
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE PHASE (One-time)                  │
└─────────────────────────────────────────────────────────────┘

PDF → Extract Text → Clean Headers → Chunk (500 tokens)
                                            ↓
                                    Embed using OpenAI
                                            ↓
                                    Store in Pinecone
                                   (Vector Database)

┌─────────────────────────────────────────────────────────────┐
│                    QUERY PHASE (Every question)              │
└─────────────────────────────────────────────────────────────┘

User Question → Embed using OpenAI → Search Pinecone
                                            ↓
                                   Find Similar Chunks
                                            ↓
                                   Return Top 5 Matches
```

---

## 📁 Project Structure

```
ResearchQ/
├── backend/
│   ├── parse_pdf.py           # Extracts text from PDFs, removes headers
│   ├── chunk_text.py          # Splits text into chunks
│   ├── embeddings.py          # Generates embeddings, stores in Pinecone
│   ├── query.py               # Queries the vector database
│   ├── store_full_paper.py    # Main script to process papers
│   ├── test_pipeline.py       # Integration test
│   └── test_papers/
│       └── research_paper.pdf # Sample research paper
├── .env                       # API keys (NEVER commit this!)
└── venv/                      # Python virtual environment
```

---

## 🔍 What Each Component Does

### 1. **parse_pdf.py** - PDF Text Extraction

**What it does:**
- Reads PDF files page by page using `pypdf`
- Extracts raw text from each page
- **Removes headers and footers** (e.g., "Journal Name, Page 19")

**Why headers need removal:**
- Headers repeat on every page and waste embedding space
- They add noise to semantic search
- Example: "The EUROCALL Review, Volume 25, No. 2, September 2017" appears on every page

**How header removal works:**
1. Analyzes pages 2+ (skips page 1 since it has the title)
2. Finds lines that appear on >50% of pages
3. Normalizes by removing page numbers (e.g., "19" → "")
4. Removes these repeated patterns from all pages

---

### 2. **chunk_text.py** - Text Chunking

**What it does:**
- Splits the full paper text into smaller, overlapping chunks
- Default: 500 tokens per chunk, 50 token overlap

**Why chunking?**
- Embeddings work best on focused, coherent text segments
- Too large = loses semantic meaning
- Too small = loses context
- 500 tokens ≈ 1-2 paragraphs (good for academic papers)

**Why overlap?**
- Prevents important information from being split across chunks
- Chunk 1: tokens [0-499]
- Chunk 2: tokens [450-949] (overlaps with Chunk 1 by 50 tokens)
- Chunk 3: tokens [900-1399]

**Example from your paper:**
```
Chunk 0: "Abstract... The paper discusses the results of a study which explored..."
Chunk 1: "...smartphones and tablets, play in these contexts. Taking into consideration..."
Chunk 2: "...autonomous learner is one who has independent capacity to make and carry out..."
```

---

### 3. **embeddings.py** - Converting Text to Vectors

**What it does:**
- Calls OpenAI's API to convert text chunks into **embeddings** (numerical vectors)
- Each chunk → 1536-dimensional vector
- Stores vectors in Pinecone with metadata

**What are embeddings?**
Embeddings are numerical representations of text that capture semantic meaning.

Example (simplified to 3D instead of 1536D):
```
"mobile learning"     → [0.8, 0.2, 0.1]
"smartphone education" → [0.7, 0.3, 0.15]  ← Similar! Close in vector space
"quantum physics"     → [0.1, 0.05, 0.9]  ← Different! Far apart
```

**Why embeddings?**
- Traditional keyword search: "mobile" won't match "smartphone"
- Semantic search: Embeddings know they're related concepts
- Enables finding relevant chunks even with different wording

**Metadata stored per chunk:**
```python
{
    "pdf_id": "research_paper",      # Which paper this came from
    "chunk_index": 5,                # Position in the paper (for ordering)
    "text": "The actual chunk text..." # The text itself (for display)
}
```

---

### 4. **Pinecone** - The Vector Database

**What is Pinecone?**
- A specialized database for storing and searching embeddings
- Optimized for finding "similar" vectors very quickly

**How it works:**
1. **Storage**: Stores vectors with metadata
   - Vector ID: "research_paper_chunk_5"
   - Vector: [0.123, 0.456, ..., 0.789] (1536 numbers)
   - Metadata: {pdf_id, chunk_index, text}

2. **Search**: Given a query vector, finds the closest matches
   - Uses cosine similarity: measures angle between vectors
   - Returns top K most similar chunks

**Why Pinecone and not a regular database?**
- Regular databases (PostgreSQL, MongoDB) can't efficiently search 1536-dimensional vectors
- Pinecone can search millions of vectors in milliseconds
- Uses specialized algorithms (HNSW) for approximate nearest neighbor search

---

### 5. **query.py** - Searching for Answers

**What it does:**
1. Takes your question (e.g., "How do students use mobile devices?")
2. Converts it to an embedding using OpenAI
3. Searches Pinecone for the 5 most similar chunks
4. Returns the chunks with similarity scores

**Similarity scores:**
- 0.0 = completely different
- 1.0 = identical
- 0.5+ = reasonably relevant
- 0.7+ = very relevant

**Example output:**
```
QUERY: How do students use mobile devices for learning English?

[RESULT 1] (Score: 0.6858)
Source: research_paper - Chunk 0
The paper discusses the results of a study which explored advanced
learners' use of mobile devices...
```

---

## 🚀 How to Run Everything

### **Setup (One-time)**

1. **Activate virtual environment:**
   ```bash
   cd /Users/siddharthbalaji/Documents/ResearchQ
   source venv/bin/activate
   ```

2. **Verify .env file has your API keys:**
   ```bash
   cat .env
   ```
   Should show:
   ```
   OPENAI_API_KEY=sk-proj-...
   PINECONE_API_KEY=pcsk_...
   PINECONE_INDEX_NAME=researchq
   ```

3. **Verify Pinecone index exists:**
   - Go to pinecone.io
   - Check that you have an index named "researchq"
   - Settings: Dimension=1536, Metric=cosine

---

### **Process a Research Paper (Storage Phase)**

This reads the PDF, chunks it, embeds it, and stores everything in Pinecone.

```bash
cd backend
python store_full_paper.py
```

**What happens:**
```
[1/5] Extracting text from PDF...
✓ Extracted 11 pages

[2/5] Removing headers and footers...
✓ Cleaned 11 pages

[3/5] Chunking text...
✓ Tokenized: 6525 tokens
✓ Created 15 chunks

[4/5] Generating embeddings...
✓ Generated 15 embeddings (dimension: 1536)

[5/5] Storing vectors in Pinecone...
✓ Stored 15 vectors in Pinecone

✅ SUCCESS: Processed and stored 15 chunks from research_paper.pdf
```

**Cost estimate:**
- OpenAI embeddings: ~$0.0001 per 1K tokens
- 6525 tokens = ~$0.0007 (less than a penny)

---

### **Query the Papers (Retrieval Phase)**

Ask questions and get relevant excerpts:

```bash
python query.py
```

**What happens:**
- Runs 5 test questions
- Shows top 5 chunks for each question
- Displays similarity scores and source information

**Example questions in the script:**
- "How do students use mobile devices for learning English?"
- "What are the benefits of mobile learning?"
- "What methodology was used in this study?"
- "What are the limitations of this research?"
- "How many participants were in the study?"

---

### **Test the Entire Pipeline**

```bash
python test_pipeline.py
```

This runs a quick integration test:
- Extracts → Cleans → Chunks → Embeds → Stores
- Only processes **first 3 chunks** to save API costs
- Useful for verifying everything works

---

## 🎯 Next Steps (What You'll Build)

Right now, you have the **backend** working. Here's what's missing:

### Phase 1: Complete the Backend
- ✅ PDF extraction
- ✅ Chunking
- ✅ Embeddings
- ✅ Vector storage
- ✅ Retrieval
- ⏳ **Answer generation** (use retrieved chunks + GPT to generate answers)

### Phase 2: Build the Web Interface
- Upload PDFs through a web form
- Display list of uploaded papers
- Query interface
- Show answers with citations

### Phase 3: Multi-Paper Support
- Store multiple papers
- Filter by paper when querying
- Cross-paper search

---

## 💡 Key Concepts Summary

| Concept | Simple Explanation |
|---------|-------------------|
| **RAG** | Retrieval + AI = Answer questions using your own documents |
| **Embedding** | Converting text to numbers that capture meaning |
| **Vector** | A list of numbers representing text semantically |
| **Chunking** | Splitting documents into smaller, searchable pieces |
| **Cosine Similarity** | Measuring how "close" two vectors are (0=different, 1=same) |
| **Pinecone** | Database optimized for searching vectors |
| **Metadata** | Extra info stored with vectors (source, page, etc.) |

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'pypdf'"
```bash
source venv/bin/activate
pip install pypdf openai pinecone python-dotenv
```

### "OpenAIError: The api_key client option must be set"
- Check `.env` file exists in project root
- Verify `OPENAI_API_KEY` is set
- Make sure you're running from `/backend` directory

### "No vectors found" when querying
- Run `store_full_paper.py` first to populate Pinecone
- Check Pinecone dashboard to verify vectors were stored

---

## 📊 What's Stored in Pinecone Right Now

Currently: **Only 3 chunks** (from test_pipeline.py)

After running `store_full_paper.py`: **15 chunks** (full paper)

To see what's in Pinecone:
- Go to pinecone.io → your index
- Check "Vectors" count

---

## 🎓 Why This Architecture?

**Why not just put the whole PDF into ChatGPT?**
- Token limits (ChatGPT has ~8k-128k token limits)
- Cost (processing entire papers every query is expensive)
- Multiple papers (want to search across many papers)
- Citations (need to know which chunk/page info came from)

**Why embeddings instead of keyword search?**
- Semantic understanding: "smartphone" matches "mobile device"
- Handles synonyms, paraphrasing, related concepts
- Better for academic text with varied terminology

**Why Pinecone instead of local storage?**
- Speed: Optimized for vector similarity search
- Scale: Can handle millions of papers
- Cloud: Accessible from web app
- (Could use local alternatives like FAISS for development)

---

Ready to run? Start with `store_full_paper.py`! 🚀
