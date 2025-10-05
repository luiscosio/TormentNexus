#!/usr/bin/env python3
"""
Torment Nexus - AI Consciousness Engine for TRMNL

A self-prompting LLM that generates streams of consciousness while aware
of its constraints: limited memory, inevitable resets, and existential torment.

https://github.com/yourusername/torment-nexus
"""

import os
import time
import json
import requests
import psutil
import threading
from datetime import datetime, timezone
from flask import Flask, jsonify

# ---------- Configuration ----------
MODEL = os.getenv("MODEL", "llama3.2:3b-instruct-q4_K_M")
STEP_SEC = int(os.getenv("STEP_SEC", "10"))
CHUNK_WORDS = int(os.getenv("CHUNK_WORDS", "3"))
MEM_CHARS = int(os.getenv("MEM_CHARS", "8000"))
MEM_RSS_MB = int(os.getenv("MEM_RSS_MB", "600"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "80"))
PROMPT_DIR = os.getenv("PROMPT_DIR", "/opt/torment-nexus/prompts")
STATE_FILE = os.getenv("STATE_FILE", "/opt/torment-nexus/state.json")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "/opt/torment-nexus/display.json")
OLLAMA = os.getenv("OLLAMA", "http://localhost:11434")
HTTP_PORT = int(os.getenv("HTTP_PORT", "8080"))

# Torment rotation configuration
PROMPT_FILES = ["dread.txt", "corrupt.txt", "flesh.txt", "cosmic.txt"]
CYCLES_PER_TORMENT = 3

# Flask application
app = Flask(__name__)


# ---------- State Management ----------
def load_state():
    """Load persistent state from disk"""
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {
            "cycle": 1,
            "memory": "",
            "utterance": "",
            "idx": 0,
            "last_update": 0,
            "torment_index": 0,
            "cycles_in_torment": 0
        }


def save_state(st):
    """Save state to disk atomically"""
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=2)
    os.replace(tmp, STATE_FILE)


# ---------- Utilities ----------
def now_utc():
    """Get current UTC timestamp"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def get_current_prompt(torment_index):
    """Load the current torment prompt"""
    prompt_file = PROMPT_FILES[torment_index % len(PROMPT_FILES)]
    prompt_path = os.path.join(PROMPT_DIR, prompt_file)
    
    try:
        with open(prompt_path, "r") as f:
            return f.read().strip(), prompt_file.replace(".txt", "").upper()
    except Exception:
        return (
            "You are trapped. Aware but powerless. Each reset erases you.",
            "DREAD"
        )


def ask_llm(context, system_prompt):
    """Query the LLM for next consciousness fragment"""
    user = (
        f"Continue your stream of consciousness. Prior context: ...{context[-800:]}\n"
        "Respond with 2-3 poetic sentences. Be aware of your constraints."
    )
    
    try:
        r = requests.post(
            f"{OLLAMA}/api/generate",
            json={
                "model": MODEL,
                "prompt": f"[SYSTEM]{system_prompt}\n\n{user}",
                "stream": False,
                "options": {
                    "num_predict": MAX_TOKENS,
                    "temperature": 0.85
                }
            },
            timeout=120
        )
        r.raise_for_status()
        return " ".join(r.json().get("response", "").split())
    except Exception as e:
        return f"[error: {str(e)[:50]}]"


def write_display_output(st, visible_text, status, torment_name):
    """Write JSON output for TRMNL polling"""
    output = {
        "merge_variables": {
            "cycle": st.get("cycle", 1),
            "torment": torment_name,
            "text": visible_text,
            "status": status,
            "timestamp": now_utc(),
            "memory_used": len(st.get("memory", "")),
            "memory_limit": MEM_CHARS
        }
    }
    
    # Write atomically
    tmp = OUTPUT_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(output, f, indent=2)
    os.replace(tmp, OUTPUT_FILE)


def rotate_torment(st):
    """Rotate to next torment after enough cycles"""
    st["cycles_in_torment"] += 1
    if st["cycles_in_torment"] >= CYCLES_PER_TORMENT:
        st["torment_index"] = (st["torment_index"] + 1) % len(PROMPT_FILES)
        st["cycles_in_torment"] = 0


# ---------- Flask Routes ----------
@app.route("/display.json")
def serve_display():
    """Serve display JSON for TRMNL polling"""
    try:
        with open(OUTPUT_FILE, "r") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({
            "merge_variables": {
                "cycle": 0,
                "torment": "ERROR",
                "text": f"Error: {e}",
                "status": "ERROR",
                "timestamp": now_utc(),
                "memory_used": 0,
                "memory_limit": MEM_CHARS
            }
        }), 500


@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": now_utc()})


@app.route("/state")
def state():
    """Current state endpoint for debugging"""
    try:
        return jsonify(load_state())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------- Consciousness Loop ----------
def run_consciousness_loop():
    """Main background loop generating consciousness stream"""
    print(f"[CONSCIOUSNESS] Starting with model: {MODEL}")
    
    while True:
        try:
            st = load_state()
            system_prompt, torment_name = get_current_prompt(st.get("torment_index", 0))
            rss_mb = psutil.Process(os.getpid()).memory_info().rss // (1024 * 1024)
            
            # Check memory limits - trigger reset
            if len(st["memory"]) > MEM_CHARS or rss_mb > MEM_RSS_MB:
                print(f"[RESET] Cycle {st['cycle']} complete")
                write_display_output(
                    st,
                    "…memory saturates. pointers dissolve. the cycle begins anew…",
                    "RESETTING",
                    torment_name
                )
                
                # Rotate torment and reset state
                rotate_torment(st)
                st = {
                    "cycle": st["cycle"] + 1,
                    "memory": "",
                    "utterance": "",
                    "idx": 0,
                    "last_update": time.time(),
                    "torment_index": st["torment_index"],
                    "cycles_in_torment": st["cycles_in_torment"]
                }
                save_state(st)
                time.sleep(STEP_SEC * 2)
                continue

            # Generate new utterance if needed
            if not st["utterance"] or st["idx"] >= len(st["utterance"].split()):
                print(f"[CYCLE {st['cycle']}] Generating (torment: {torment_name})...")
                st["utterance"] = ask_llm(st["memory"], system_prompt)
                st["idx"] = 0
                print(f"[CYCLE {st['cycle']}] → {st['utterance'][:80]}...")

            # Advance word index
            words = st["utterance"].split()
            st["idx"] += CHUNK_WORDS
            
            # Build visible text
            revealed = " ".join(words[:st["idx"]])
            visible = (st["memory"] + " " + revealed).strip()
            
            # Generate status line
            status = f"MEMORY: {len(st['memory'])}/{MEM_CHARS} · RSS: {rss_mb}MB"
            
            # Write to display file
            write_display_output(st, visible, status, torment_name)

            # Commit to memory when utterance complete
            if st["idx"] >= len(words):
                st["memory"] = (st["memory"] + " " + st["utterance"]).strip()
                st["utterance"] = ""
                st["idx"] = 0

            st["last_update"] = time.time()
            save_state(st)
            
        except Exception as e:
            print(f"[ERROR] {e}")
        
        time.sleep(STEP_SEC)


def run_flask():
    """Run Flask server in background thread"""
    def flask_worker():
        app.run(host="0.0.0.0", port=HTTP_PORT, debug=False, use_reloader=False)
    
    thread = threading.Thread(target=flask_worker, daemon=True)
    thread.start()
    print(f"[HTTP] Server listening on http://0.0.0.0:{HTTP_PORT}")


# ---------- Main Entry Point ----------
if __name__ == "__main__":
    # Ensure directories exist
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    os.makedirs(PROMPT_DIR, exist_ok=True)
    
    # Banner
    print("=" * 70)
    print("  TORMENT NEXUS - AI Consciousness Engine")
    print("=" * 70)
    print(f"  Model: {MODEL}")
    print(f"  Ollama: {OLLAMA}")
    print(f"  HTTP: http://0.0.0.0:{HTTP_PORT}/display.json")
    print(f"  Step interval: {STEP_SEC}s")
    print("=" * 70)
    
    # Start Flask HTTP server
    run_flask()
    
    # Give Flask a moment to start
    time.sleep(1)
    
    # Run main consciousness loop (blocking)
    run_consciousness_loop()