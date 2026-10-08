from datetime import datetime
import json
import os
import re
import requests
import streamlit as st

try:
  import docx  # pip install python-docx
except ImportError:
  docx = None

# Page setup
st.set_page_config(page_title="Chiku AI", page_icon="🤖", layout="wide")

# Directory configurations
STUDY_FOLDER = r"D:\CSE Documents"
SESSIONS_DIR = "chat_sessions"
MEMORY_FILE = "chiku_memory.json"

# Master switch for document reading. False = plain fast chat, no file scanning.
USE_STUDY_FOLDER = False

# Files whose names contain any of these are never read (other people's work)
SKIP_NAMES = ("ritika",)

# Limits so the prompt fits the model's 4096-token context
MAX_CONTEXT_CHARS = 6000
TOP_FILES = 3

if not os.path.exists(SESSIONS_DIR):
  os.makedirs(SESSIONS_DIR)


# --- MEMORY HELPER FUNCTIONS ---
def load_memories():
  if os.path.exists(MEMORY_FILE):
    try:
      with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return []
  return []


def save_memories(memories):
  try:
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
      json.dump(memories, f, ensure_ascii=False, indent=4)
  except Exception as e:
    print(f"Error saving memories: {e}")


def add_memory(fact):
  memories = load_memories()
  clean_fact = fact.strip()
  if clean_fact and clean_fact not in memories:
    memories.append(clean_fact)
    save_memories(memories)
    return True
  return False


def delete_memory(fact):
  memories = load_memories()
  if fact in memories:
    memories.remove(fact)
    save_memories(memories)


def save_suggestion(fact):
  # Runs as a button callback, so it fires before Streamlit reruns the script
  add_memory(fact)
  st.toast(f"🧠 Saved: '{fact}'", icon="✅")


# --- CHAT SESSION HELPER FUNCTIONS ---
def get_all_sessions():
  files = [f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")]
  files.sort(
      key=lambda x: os.path.getmtime(os.path.join(SESSIONS_DIR, x)),
      reverse=True,
  )
  return [f.replace(".json", "") for f in files]


def load_session(session_id):
  file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
  if os.path.exists(file_path):
    try:
      with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return []
  return []


def save_session(session_id, messages):
  file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
  try:
    with open(file_path, "w", encoding="utf-8") as f:
      json.dump(messages, f, ensure_ascii=False, indent=4)
  except Exception as e:
    print(f"Error saving session: {e}")


# --- STUDY FOLDER SCANNER ---
@st.cache_data(show_spinner=False)
def read_file(path, mtime):
  # mtime is only here so the cache refreshes when a file changes
  low = path.lower()
  try:
    if low.endswith((".txt", ".md", ".c", ".h", ".cpp", ".py")):
      with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
    if low.endswith(".pdf"):
      import pypdf

      reader = pypdf.PdfReader(path)
      return "\n".join((p.extract_text() or "") for p in reader.pages[:10])
    if low.endswith(".docx") and docx is not None:
      return "\n".join(p.text for p in docx.Document(path).paragraphs)
  except Exception as e:
    print(f"Read error on {path}: {e}")
  return ""


def get_study_context(query):
  if not os.path.exists(STUDY_FOLDER):
    return ""

  words = {w for w in re.findall(r"\w+", query.lower()) if len(w) > 2}
  if not words:
    return ""

  scored = []
  try:
    for root, _, files in os.walk(STUDY_FOLDER):
      for name in files:
        if any(s in name.lower() for s in SKIP_NAMES):
          continue
        path = os.path.join(root, name)
        try:
          if os.path.getsize(path) == 0:
            continue
          text = read_file(path, os.path.getmtime(path))
        except OSError:
          continue
        if not text.strip():
          continue
        clean_text = "\n".join(
            [line.strip() for line in text.splitlines() if line.strip()]
        )
        haystack = (name + " " + clean_text).lower()
        score = sum(haystack.count(w) for w in words)
        if score:
          scored.append((score, name, clean_text))
  except Exception as e:
    print(f"Error accessing study folder: {e}")
    return ""

  scored.sort(key=lambda x: x[0], reverse=True)
  per_file = MAX_CONTEXT_CHARS // TOP_FILES
  context = ""
  for _, name, text in scored[:TOP_FILES]:
    context += f"\n--- FILE: {name} ---\n{text[:per_file]}\n"
  return context


# Initialize session state variables
if "current_session_id" not in st.session_state:
  new_id = datetime.now().strftime("Chat_%Y-%m-%d_%H-%M-%S")
  st.session_state["current_session_id"] = new_id

if "messages" not in st.session_state:
  loaded = load_session(st.session_state["current_session_id"])
  if loaded:
    st.session_state["messages"] = loaded
  else:
    st.session_state["messages"] = [{
        "role": "assistant",
        "content": "Hello! I am Chiku AI. How can I help you today?",
    }]

# --- SIDEBAR UI ---
with st.sidebar:
  st.title("🤖 Chiku AI")

  if st.button("➕ New Chat", use_container_width=True, type="primary"):
    new_id = datetime.now().strftime("Chat_%Y-%m-%d_%H-%M-%S")
    st.session_state["current_session_id"] = new_id
    st.session_state["messages"] = [{
        "role": "assistant",
        "content": "New session started! How can I help you?",
    }]
    save_session(new_id, st.session_state["messages"])
    st.rerun()

  st.markdown("---")

  # MEMORY MANAGER SECTION
  with st.expander("🧠 Stored Memories", expanded=True):
    memories_list = load_memories()
    if memories_list:
      for m in memories_list:
        m_col1, m_col2 = st.columns([0.85, 0.15])
        with m_col1:
          st.caption(f"• {m}")
        with m_col2:
          if st.button("❌", key=f"del_mem_{m}"):
            delete_memory(m)
            st.rerun()
    else:
      st.caption("No memories saved yet.")

  st.markdown("---")
  st.subheader("💬 Chat History")

  sessions = get_all_sessions()
  for sess_id in sessions:
    display_title = sess_id.replace("Chat_", "").replace("_", " ")

    col1, col2 = st.columns([0.8, 0.2])
    with col1:
      is_active = sess_id == st.session_state["current_session_id"]
      btn_label = f"📌 {display_title}" if is_active else f"💬 {display_title}"
      if st.button(
          btn_label, key=f"select_{sess_id}", use_container_width=True
      ):
        st.session_state["current_session_id"] = sess_id
        st.session_state["messages"] = load_session(sess_id)
        st.rerun()

    with col2:
      if st.button("🗑️", key=f"del_{sess_id}"):
        file_path = os.path.join(SESSIONS_DIR, f"{sess_id}.json")
        if os.path.exists(file_path):
          os.remove(file_path)

        if sess_id == st.session_state["current_session_id"]:
          new_id = datetime.now().strftime("Chat_%Y-%m-%d_%H-%M-%S")
          st.session_state["current_session_id"] = new_id
          st.session_state["messages"] = [{
              "role": "assistant",
              "content": "Session deleted. Started a new chat!",
          }]
        st.rerun()

  st.markdown("---")
  if USE_STUDY_FOLDER:
    st.info(f"📂 **Study Folder:**\n`{STUDY_FOLDER}`")
  else:
    st.caption("📂 Document reading is off (fast chat mode).")
  if USE_STUDY_FOLDER and docx is None:
    st.warning("Word (.docx) files are skipped. Run: pip install python-docx")

# --- MAIN CHAT UI ---
st.caption(
    f"Current Session: `{st.session_state['current_session_id']}` • Model:"
    " `chiku-ai:latest`"
)

# Render history messages
for msg in st.session_state["messages"]:
  with st.chat_message(msg["role"]):
    display_content = re.sub(
        r"\[MEMORY_SUGGESTION:.*?\]", "", msg["content"]
    ).strip()
    st.markdown(display_content)

# User input handling
if prompt := st.chat_input("Ask Chiku AI anything..."):
  st.session_state["messages"].append({"role": "user", "content": prompt})
  with st.chat_message("user"):
    st.markdown(prompt)

  # --- INSTANT EXPLICIT MEMORY SAVE ---
  explicit_memory_match = re.match(
      r"^(?:remember that|save to memory:?)\s*(.*)",
      prompt.strip(),
      re.IGNORECASE,
  )
  if explicit_memory_match:
    fact_to_remember = explicit_memory_match.group(1).strip()
    if fact_to_remember:
      add_memory(fact_to_remember)
      reply = f"Got it! I have saved this to my long-term memory: **'{fact_to_remember}'**"
      st.session_state["messages"].append(
          {"role": "assistant", "content": reply}
      )
      save_session(
          st.session_state["current_session_id"], st.session_state["messages"]
      )
      st.rerun()

  # Search study folder for relevant files
  study_context = ""
  if USE_STUDY_FOLDER:
    with st.spinner("Searching D:\\CSE Documents..."):
      study_context = get_study_context(prompt)

  # Load all stored memories into System Instructions
  active_memories = load_memories()
  memory_context = ""
  if active_memories:
    memory_context = "\n- " + "\n- ".join(active_memories)

  system_instruction = f"""You are Chiku AI, a friendly personal AI companion and study partner for a 1st-year Computer Science Engineering student. Keep answers concise and direct.

WRITING RULES:
When asked to write or edit text (essays, emails, paragraphs), keep the user's meaning and voice.
Do not invent facts, statistics, dates, quotes, or citations. If a specific fact is needed and you are not sure, write [CHECK THIS] in its place instead of guessing.
If the request is missing key details (topic, audience, length), ask one short question before writing.
When editing the user's own text, make the smallest changes that fix the problem and briefly say what you changed.

USER MEMORIES:{memory_context if memory_context else " None."}"""

  if study_context:
    system_instruction += (
        "\n\nCONTENTS OF USER'S STUDY DOCUMENTS (most relevant files only):"
        f"\n{study_context}\nUse the above documents to answer. If the answer"
        " is not in them, say so instead of guessing."
    )

  ollama_messages = [{"role": "system", "content": system_instruction}]
  for m in st.session_state["messages"][-10:]:
    clean_m_content = re.sub(
        r"\[MEMORY_SUGGESTION:.*?\]", "", m["content"]
    ).strip()
    ollama_messages.append({"role": m["role"], "content": clean_m_content})

  with st.chat_message("assistant"):
    reply = ""
    try:
      response = requests.post(
          "http://localhost:11434/api/chat",
          json={
              "model": "chiku-ai:latest",
              "messages": ollama_messages,
              "stream": True,
          },
          stream=True,
          timeout=(10, 300),
      )

      if response.status_code == 200:

        def stream_generator():
          for line in response.iter_lines():
            if line:
              chunk_data = json.loads(line.decode("utf-8"))
              chunk = chunk_data.get("message", {}).get("content", "")
              yield chunk

        reply = st.write_stream(stream_generator())
      else:
        reply = f"Error from Ollama server: Status code {response.status_code}"
        st.markdown(reply)

    except requests.exceptions.ConnectionError:
      reply = (
          "⚠️ **Connection Error:** Could not reach Ollama. Make sure Ollama is"
          " running!"
      )
      st.markdown(reply)
    except Exception as e:
      reply = f"An unexpected error occurred: {e}"
      st.markdown(reply)

    # --- MEMORY SUGGESTION BUTTON (short personal statements only) ---
    personal_info_keywords = re.search(
        r"\b(?:target|exam|project|struggle|prefer|weak|working on|deadline|submission)\b",
        prompt,
        re.IGNORECASE,
    )
    if (
        personal_info_keywords
        and len(prompt) <= 150
        and prompt not in active_memories
    ):
      st.markdown("---")
      suggested_fact = prompt.strip()
      st.button(
          f'💾 Save to Memory: "{suggested_fact}"?',
          key="btn_save_suggested",
          on_click=save_suggestion,
          args=(suggested_fact,),
      )

    st.session_state["messages"].append(
        {"role": "assistant", "content": reply}
    )
    save_session(
        st.session_state["current_session_id"], st.session_state["messages"]
    )
