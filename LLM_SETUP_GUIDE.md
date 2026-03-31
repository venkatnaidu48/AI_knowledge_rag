# 🚀 LLM Setup Guide - Fix Your Query Errors

## ❌ What Went Wrong

Your interactive demo had **2 issues**:

### Issue 1: No LLM Provider Running
```
Mistral generation failed: Ollama error: {"error":"model 'mistral' not found"}
```
**Cause**: Mistral/Ollama wasn't installed or running

### Issue 2: Code Bug
```
AttributeError: 'GenerationResponse' object has no attribute 'get'
```
**Cause**: Code was treating GenerationResponse object as a dictionary
**Fix**: ✅ Already fixed in interactive_demo.py

---

## ✅ Setup Instructions: Choose One Option

### **Option 1: Mistral (FREE, LOCAL) ⭐ Recommended**

**Best for**: Quick testing, privacy, no costs

#### Step 1: Install Ollama
1. Download from https://ollama.ai
2. Install and run
3. A window will open - keep it running

#### Step 2: Pull Mistral Model
Open a terminal and run:
```bash
ollama pull mistral
```

This downloads the model (~4GB) - wait for it to complete:
```
✅ success
```

#### Step 3: Verify Installation
```bash
ollama list
```

You should see:
```
NAME      ID              SIZE    MODIFIED
mistral   2dfb92effa37    4.1 GB  2 minutes ago
```

#### Step 4: Test Your Demo
```bash
cd c:\Users\VENKATADRI\Downloads\Desktop\codes\ragapplication
python scripts/interactive_demo.py
```

---

### **Option 2: OpenAI (PAID, BEST QUALITY)**

**Cost**: ~$0.03-0.30 per query
**Quality**: Excellent ✨

#### Step 1: Get API Key
1. Go to https://platform.openai.com/api/keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-`)

#### Step 2: Create .env File
Create file: `c:\Users\VENKATADRI\Downloads\Desktop\codes\ragapplication\.env`

Add:
```
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-4
```

#### Step 3: Test Your Demo
```bash
python scripts/interactive_demo.py
```

---

### **Option 3: Groq (FAST, FREE TIER) 🚀**

**Cost**: FREE (with rate limits)
**Speed**: Very fast

#### Step 1: Get API Key
1. Go to https://console.groq.com
2. Sign up free
3. Create API key
4. Copy the key (starts with `gsk_`)

#### Step 2: Create .env File
Create file: `c:\Users\VENKATADRI\Downloads\Desktop\codes\ragapplication\.env`

Add:
```
GROQ_API_KEY=gsk_your-actual-key-here
GROQ_MODEL=mixtral-8x7b-32768
```

#### Step 3: Test Your Demo
```bash
python scripts/interactive_demo.py
```

---

### **Option 4: HuggingFace (FREE CLOUD)**

**Cost**: FREE (with rate limits)
**Speed**: Medium

#### Step 1: Get API Key
1. Go to https://huggingface.co
2. Sign up free
3. Go to Settings → Access Tokens
4. Create Token
5. Copy the token

#### Step 2: Create .env File
Create file: `c:\Users\VENKATADRI\Downloads\Desktop\codes\ragapplication\.env`

Add:
```
HF_API_KEY=hf_your-actual-token-here
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.1
```

#### Step 3: Test Your Demo
```bash
python scripts/interactive_demo.py
```

---

## 🧪 Test Your Setup

After choosing an option, run:

```bash
python scripts/interactive_demo.py
```

Then ask a question:
```
>>> What is Director Orientation?
```

✅ **Success looks like**:
```
⏳ STEP 1: Searching Knowledge Base...
✅ Found X relevant chunks

⏳ STEP 2: Generating Answer...
✅ Answer generated successfully

📝 GENERATED ANSWER:
[Your answer here]

⏳ STEP 3: Validating Answer Quality...
✅ VALIDATION RESULTS:
Overall Quality Score: 85.00%
Quality Rating: 🟢 EXCELLENT - High Confidence
```

---

## 📋 Comparison Table

| Feature | Mistral | OpenAI | Groq | HuggingFace |
|---------|---------|--------|------|-------------|
| **Cost** | FREE | $ | FREE* | FREE* |
| **Setup** | ⭐ Easy | Easy | Easy | Easy |
| **Speed** | Medium | Fast | Very Fast | Medium |
| **Quality** | Good | Excellent | Good | Medium |
| **Privacy** | Local ✓ | Cloud ✗ | Cloud ✗ | Cloud ✗ |
| **Recommended** | ✅ Dev | ✅ Prod | ✅ Speed | Okay |

*Free tier has rate limits

---

## 🐛 Code Fixes Applied

Automatic fixes have been applied to `scripts/interactive_demo.py`:

### Fix 1: GenerationResponse Handling
**Before**:
```python
if not gen_result.get("success"):  # ❌ GenerationResponse has no .get()
```

**After**:
```python
if gen_result is None:  # ✅ Check if None
```

### Fix 2: Response Text Access
**Before**:
```python
answer = gen_result.get("response", "")  # ❌ Wrong
```

**After**:
```python
answer = gen_result.response_text  # ✅ Correct attribute
```

### Fix 3: Validation Result Handling
**Before**:
```python
overall_score = val_result.get("overall_score", 0)  # ❌ Not a dict
```

**After**:
```python
overall_score = val_result.overall_score  # ✅ Pydantic model attribute
```

---

## 🔧 Troubleshooting

### Error: "model 'mistral' not found"
- **Solution**: Make sure Ollama is still running (check taskbar)
- **Or**: Run `ollama pull mistral` again

### Error: "OPENAI_API_KEY not found"
- **Solution**: Create `.env` file in project root
- **Verify**: File should be in: `c:\Users\VENKATADRI\Downloads\Desktop\codes\ragapplication\.env`

### Error: "Connection refused"
- **Solution**: Your LLM provider isn't responding
- **Try**: Switch to a different provider (Mistral → Groq)

### Error: "Rate limit exceeded"
- **Solution**: Free tiers have limits (usually 30 requests/min)
- **Try**: Wait a minute before retrying

### Still getting errors?
1. Check the diagnostics:
```bash
python check_metadata.py
python diagnose_faiss.py
```

2. Check logs:
```bash
tail -f logs/debug.log
```

---

## ✨ Next Steps

After setup works, try:

1. **Upload more documents**:
   - Go to http://localhost:8000/docs
   - POST /api/v1/documents/upload

2. **Ask different questions**:
   - "What are the main policies?"
   - "How do we handle security?"
   - "What is the company strategy?"

3. **Monitor responses**:
   - Quality scores should be 0.7+
   - Grounding score shows if answer is based on documents

4. **Scale up**:
   - Add more documents
   - Run batch processing
   - Set up production deployment

---

## 📞 Need Help?

Check these files:
- [README.md](README.md) - Project overview
- [README_END_TO_END.md](README_END_TO_END.md) - Detailed workflow
- [STEP_BY_STEP_GUIDE.md](STEP_BY_STEP_GUIDE.md) - All 8 steps explained
- [QUICK_START_DEMO.md](QUICK_START_DEMO.md) - Quick start guide

Good luck! 🚀
