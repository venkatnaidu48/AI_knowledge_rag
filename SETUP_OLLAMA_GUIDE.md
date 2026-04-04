# OPTION B: OLLAMA LOCAL MODEL SETUP (Windows)

## What is Ollama?
- **Free** local LLM server that runs on your computer
- **No API calls** = No cost, No quota limits, Full privacy
- **Fast** = <500ms response time (local, no network latency)
- **Fallback** = Auto-switches to Ollama if Groq/OpenAI fail

---

## STEP 1: Install Ollama (5 minutes)

### Option A: Using Installer (Easiest) ✅ RECOMMENDED
1. Download: https://ollama.ai/download
2. Choose **Windows** 
3. Run installer `OllamaSetup.exe`
4. Follow prompts (all defaults are fine)
5. **Restart your computer** after install

### Option B: Manual Setup (If installer fails)
1. Install Docker Desktop: https://www.docker.com/products/docker-desktop
2. After Docker starts, open PowerShell and run:
   ```powershell
   docker run -d --name ollama -p 11434:11434 ollama/ollama
   ```

**Verify Installation:**
- Open Command Prompt
- Run: `ollama --version`
- Should show version number

---

## STEP 2: Pull Mistral Model (3 minutes)

Open **Command Prompt** and run:

```cmd
ollama pull mistral
```

This downloads the Mistral model (~4GB). First time takes 2-3 minutes.

**What you'll see:**
```
pulling manifest
pulling 84d8d10270f9... 100% ▓▓▓▓▓▓▓▓▓▓ 2.6 GB
pulling 3a3c6b34c5fb... 100% ▓▓▓▓▓▓▓▓▓▓ 106 B
pulling ed11ed7ff44d... 100% ▓▓▓▓▓▓▓▓▓▓ 366 B
verifying sha256 digest
writing manifest
success
```

---

## STEP 3: Verify Ollama is Running

Ollama runs automatically in background. To verify it's responding:

```cmd
curl http://localhost:11434/api/tags
```

Or use our verification script (see below).

---

## STEP 4: Your RAG App Auto-Configuration

Already configured! No changes needed. The RAG app will:

1. **Try OpenAI first** (when you add credits later) ✅
2. **Fallback to Ollama** (local, FREE) ✅  
3. **Fallback to Groq** (if Ollama somehow fails) ✅

---

## Testing

After Ollama is installed and mistral model is downloaded, run:

```cmd
python test_all_providers.py
```

You should see:
```
Provider Status:
✅ Ollama (Local Mistral)
✅ Groq (Fast Inference)
⚠️ OpenAI (waiting for credits)
```

---

## Troubleshooting

### "ollama command not found"
→ Restart Command Prompt or computer after installation

### "Connection refused to localhost:11434"
→ Ollama not running. Run: `ollama serve` in new Command Prompt

### "Model pull timeout"
→ Network issue. Try again with good internet connection

### Low system performance while Ollama runs
→ Normal! Mistral uses ~7GB RAM. Restart Ollama if not needed

---

## When to Use Which Model

| Scenario | Model | Command |
|----------|-------|---------|
| **Now (no money)** | Ollama | Default ✅ |
| **Testing/Dev** | Ollama | Fast, Free |
| **Add $$ to OpenAI** | OpenAI Auto | System switches automatically |
| **Backup (Groq fails)** | Groq | Auto fallback |

---

## Managing Ollama

**Start Ollama:**
```cmd
ollama serve
```

**Stop Ollama:**
- Press `Ctrl+C` in the Command Prompt window

**Restart Ollama:**
```cmd
ollama serve
```

**Update/Reinstall Model:**
```cmd
ollama pull mistral --latest
```

---

## NEXT STEPS

1. ✅ Download & Install Ollama (5 min)
2. ✅ Pull Mistral model (3 min)  
3. ✅ Run verification script
4. ✅ Test RAG pipeline with local model
5. 🔄 When you add OpenAI credit → System auto-upgrades
