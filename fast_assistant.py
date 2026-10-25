import os
import sys
import socket
import urllib.request
import urllib.parse
import json
import re
import requests
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KIWIX_BASE = "http://localhost:8088"
OLLAMA_URL = "http://localhost:11434/api/generate"

STOP_WORDS = {"how", "do", "i", "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is", "can", "what", "why", "with", "write", "an", "essay"}

def is_online(timeout=1.0):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("1.1.1.1", 53))
        return True
    except Exception:
        return False

def extract_keywords(query):
    words = re.findall(r'\b[a-zA-Z0-9_+#\.]+\b', query)
    keywords = [w for w in words if w.lower() not in STOP_WORDS]
    return " ".join(keywords[:5]) if keywords else query

def search_offline_vault(query):
    clean_search = extract_keywords(query)
    try:
        url = f"{KIWIX_BASE}/search?pattern={urllib.parse.quote(clean_search)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=1.5) as res:
            html = res.read().decode('utf-8', errors='ignore')
        
        matches = re.findall(r'href="(/[^"]+/[^"]+)"', html)
        clean = [m for m in matches if not any(x in m for x in ['.css', '.js', '.png', '.ico', '/skin/'])]
        if clean:
            top_path = clean[0]
            art_req = urllib.request.Request(f"{KIWIX_BASE}{top_path}", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(art_req, timeout=1.5) as art_res:
                soup = BeautifulSoup(art_res.read().decode('utf-8', errors='ignore'), "html.parser")
                for tag in soup(["script", "style", "nav", "footer"]):
                    tag.decompose()
                return top_path, " ".join(soup.stripped_strings)[:1500]
        return None, ""
    except Exception:
        return None, ""

def search_online_duckduckgo(query):
    try:
        clean_q = extract_keywords(query)
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(clean_q)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=2.5) as res:
            soup = BeautifulSoup(res.read().decode('utf-8', errors='ignore'), "html.parser")
            snippets = [s.get_text() for s in soup.find_all("a", class_="result__snippet")[:2]]
            return " ".join(snippets)[:1200]
    except Exception:
        return ""

def query_llm(prompt, model="qwen2.5:3b", context="", source_type="Internal Weights"):
    full_prompt = (
        f"Context from {source_type}:\n\"\"\"{context}\"\"\"\n\n"
        f"Instruction: Use the context above to deliver an accurate, direct answer or essay.\n"
        f"User Prompt: {prompt}"
    ) if context else prompt

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": True,
        "options": {
            "num_predict": 750,
            "num_ctx": 2048,
            "temperature": 0.4 if "3b" in model else 0.2
        }
    }
    
    try:
        res = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=None)
        for line in res.iter_lines():
            if line:
                chunk = json.loads(line.decode('utf-8'))
                print(chunk.get("response", ""), end="", flush=True)
        print("\n")
    except Exception as e:
        print(f"\n[Error contacting Ollama]: {e}")

def main():
    online_status = is_online()
    print("=" * 70)
    print(" SPARKVAULT PORTABLE HYBRID (OFFLINE + ONLINE AUTO-ROUTING)")
    print(f" Network Status: [{'ONLINE' if online_status else 'OFFLINE - Vault Only'}]")
    print(" [Default] Fast 3B Engine | [code:] 7B Coder | [r1:] 7B Reasoning")
    print("=" * 70)

    while True:
        try:
            user_input = input("\nAsk (or 'exit'): ").strip()
            if not user_input or user_input.lower() in ["exit", "quit"]:
                break

            if user_input.startswith("r1:"):
                selected_model = "deepseek-r1:7b"
                clean_query = user_input[3:].strip()
            elif user_input.startswith("code:"):
                selected_model = "spark-coder:7b"
                clean_query = user_input[5:].strip()
            else:
                selected_model = "qwen2.5:3b"
                clean_query = user_input

            context = ""
            source_label = ""

            print("\n[1/2] Searching local vault...", end=" ")
            top_link, offline_text = search_offline_vault(clean_query)

            if offline_text:
                print(f"Found offline article: {top_link}")
                context = offline_text
                source_label = "Local Offline Vault"
            elif is_online():
                print("No offline hit. Querying live web...", end=" ")
                web_text = search_online_duckduckgo(clean_query)
                if web_text:
                    print("Found live web results.")
                    context = web_text
                    source_label = "Live Web"
                else:
                    print("Synthesizing from neural weights.")
            else:
                print("No direct text hit; synthesizing from local weights.")

            print(f"[2/2] Streaming [{selected_model}]:\n")
            query_llm(clean_query, model=selected_model, context=context, source_type=source_label)

        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
