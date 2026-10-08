# Chiku-AI
A fully offline personal AI study companion. It runs on a local model through [Ollama](https://ollama.com), with a simple Streamlit chat interface. No internet is needed after setup, and nothing leaves your computer.

Built as a learning project by a first-year CSE student, **with AI assistance**.
<img width="538" height="455" alt="Screenshot 2026-10-08 223100" src="https://github.com/user-attachments/assets/eadf52d8-a820-495f-94ed-4f723cf219a1" />


## Features

- Chat with a local LLM (Qwen3 4B Instruct) with live streaming replies
- Multiple chat sessions, saved locally and listed in the sidebar
- Long-term memory: tell it `remember that ...` and it keeps the fact across chats
- Suggests saving personal facts (exams, deadlines, preferences) with one click
- Writing rules in the system prompt: it avoids inventing facts and marks them `[CHECK THIS]`

## Tested on

- Ryzen 3 5300U, 16 GB RAM, integrated graphics, Windows 11
- About 9-11 tokens/sec for plain chat (CPU only)

Slower or lower-RAM machines will be slower. 16 GB RAM is recommended.

## Setup (Windows)

1. Install [Ollama](https://ollama.com/download).
2. Install [Python 3.10+](https://www.python.org/downloads/) and tick "Add Python to PATH" during install.
3. Download this repository (Code > Download ZIP) and unzip it.
4. Open PowerShell in the unzipped folder and run:
(Remember to run these commands in Adminstrator mode and one by one.)

```powershell
pip install -r requirements.txt
ollama pull qwen3:4b-instruct-2507-q4_K_M
ollama create chiku-ai -f Modelfile
streamlit run app.py
```

The model download is about 2.5 GB. If the `ollama pull` tag is not found, check the exact name at [ollama.com/library/qwen3/tags](https://ollama.com/library/qwen3/tags) and update the `FROM` line in `Modelfile` to match.

After the first setup, you only need `streamlit run app.py` (with Ollama running).

## Using it

- Type normally to chat.
- `remember that my exam is on 15 November` saves a fact. It appears under "Stored Memories" in the sidebar, where you can delete it.
- Use **New Chat** to start a fresh session. Old sessions stay in the sidebar.

## Limitations (please read)

- It is a small 4B model. It can be wrong while sounding confident, so verify anything important against your notes or textbook.
- It has no internet access, so it cannot look things up.
- Replies are slow on CPU-only laptops.
- Chat history and memory are stored as plain JSON files (`chat_sessions/` and `chiku_memory.json`) next to the app. They are not encrypted.
- Reading your own documents is **experimental and switched off by default** (`USE_STUDY_FOLDER = False` in `app.py`). It is crude keyword matching, does not read `.pptx` or scanned PDFs, and slows replies a lot. Use at your own risk.
- Tested on Windows only.

## Project files

| File | Purpose |
|---|---|
| `app.py` | The whole app: chat UI, sessions, memory |
| `Modelfile` | Builds the `chiku-ai` model from Qwen3 4B Instruct with a custom system prompt |
| `requirements.txt` | Python packages |

## Lessons learned

- `qwen3:4b` on Ollama resolved to a thinking-only variant on my setup, so `/no_think` and `--think=false` did not turn reasoning off and a simple question took minutes. Switching to the `instruct-2507` variant fixed it.
- Putting retrieved document text in every prompt is expensive on a CPU, so plain chat is much faster than file Q&A.

## License

MIT
