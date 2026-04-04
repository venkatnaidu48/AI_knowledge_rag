# HOW TO USE YOUR RAG SYSTEM - QUICK START

## 🚀 FASTEST WAY TO GET ANSWERS (Recommended)

### Method 1: Single Command
```bash
.venv\Scripts\python.exe quick_qa.py "What is IIMA?"
```

### Method 2: Interactive Mode
```bash
run_qa.bat
```

### Method 3: Command Line - Multiple Questions
```bash
.venv\Scripts\python.exe quick_qa.py "What are policies?"
.venv\Scripts\python.exe quick_qa.py "Tell me about benefits"
.venv\Scripts\python.exe quick_qa.py "What are security guidelines?"
```

---

## 📊 WHY These Methods Are Recommended

### Quick Q&A (✅ WORKING - INSTANT)
- **Speed:** <1 second per query
- **Method:** Direct document extraction
- **Requires:** Nothing extra
- **Best for:** Immediate answers from documents

### Ollama LLM (⏳ SLOW - Could be 30-120s per query)
- **Speed:** 30-120+ seconds per query  
- **Method:** AI-powered generation
- **Requires:** Ollama running + models loaded
- **Best for:** Enhanced/paraphrased answers

---

## 🎯 Live Demo - Q&A Examples

### Question 1
```bash
> .venv\Scripts\python.exe quick_qa.py "What is the company?"

[ANSWER - EXTRACTED FROM DOCUMENTS]
--- Page 1 ---
HUMAN RESOURCES POLICY MANUAL STAFF 2023
IIMA HR Policy Manual 2023

The objective of this Manual is to compile the HR policies...
```

### Question 2
```bash
> .venv\Scripts\python.exe quick_qa.py "What are security guidelines?"

[ANSWER - EXTRACTED FROM DOCUMENTS]
IIMA provides comprehensive security guidelines including...
[Results with source]
```

### Question 3
```bash
> .venv\Scripts\python.exe quick_qa.py "Tell me about employees"

[ANSWER - EXTRACTED FROM DOCUMENTS]
Employee management policies at IIMA include...
```

---

## 📋 Complete Setup

### First Time Only
```bash
# 1. Activate environment
.venv\Scripts\activate.bat

# 2. Test system
.venv\Scripts\python.exe test_system.py
```

### Every Time You Want Q&A
```bash
# Option A: Interactive
run_qa.bat

# Option B: Single question
.venv\Scripts\python.exe quick_qa.py "Your question?"

# Option C: FastAPI (if needed for integration)
.venv\Scripts\python.exe api_query.py
```

---

## ✨ Features

✅ **39 Documents loaded** (company policies, HR manual)
✅ **34,627 chunks indexed** (searchable)  
✅ **Instant results** (<1 second)
✅ **Source attribution** (shows where answer came from)
✅ **No internet needed** (local only)
✅ **Works without Ollama** (document extraction mode)

---

## 📞 If You Want AI-Powered Answers (Optional)

If you want paraphrased/enhanced answers using Mistral LLM:

1. Wait for Ollama model to load (first run: 1-2 minutes)
2. Then use: `.venv\Scripts\python.exe scripts\retrieve_answers.py "question"`
3. Will be slower (30-120s per query) but more advanced answers

**For now, use `quick_qa.py` for instant, reliable results!**
