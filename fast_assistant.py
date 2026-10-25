import urllib.request
import urllib.parse
import json
import re
import requests
from bs4 import BeautifulSoup

KIWIX_BASE = "http://localhost:8088"
OLLAMA_URL = "http://localhost:11434/api/generate"
STOP_WORDS = {"how", "do", "i", "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is", "can", "what", "why", "with", "write", "an", "essay"}

def extract_keywords(query):
    words = re.findall(r'\b[a-zA-Z0-9_+#\.]+\b', query)
    keywords = [w for w in words if w.lower() not in STOP_WORDS]
    return " ".join(keywords[:5]) if keywords else query

def get_article_text(article_path):
    """Fetches the actual text content from the offline ZIM archive."""
    try:
        url = f"{KIWIX_BASE}{article_path}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=1.5) as res:
            html = res.read().decode('utf-8', errors='ignore')
        
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        
        text = " ".join(soup.stripped_strings)
        return text[:1500]  # First 1500 chars of verified source material
    except Exception:
        return ""

def search_offline_vault(query):
    clean_search = extract_keywords(query)
    try:
        url = f"{KIWIX_BASE}/search?pattern={urllib.parse.quote(clean_search)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=2.0) as res:
            html = res.read().decode('utf-8', errors='ignore')
        
        matches = re.findall(r'href="(/[^"]+/[^"]+)"', html)
        clean = [m for m in matches if not any(x in m for x in ['.css', '.js', '.png', '.ico', '/skin/'])]
        
        if clean:
            top_path = clean[0]
            content = get_article_text(top_path)
            return top_path, content
        return None, ""
    except Exception:
        return None, ""

def query_llm(prompt, model="qwen2.5:3b", raw_context=""):
    full_prompt = (
        f"Verified Facts from Database:\n\"\"\"{raw_context}\"\"\"\n\n"
        f"Instruction: Use the facts above to answer or write the essay accurately.\n"
        f"User Prompt: {prompt}"
    ) if raw_context else prompt

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
    print("=" * 68)
    print(" SPARKVAULT TRUE RAG (20 BOOKS FULL-TEXT + 3B/7B LLMS)")
    print(" [Default] Fast 3B + Full Database Extraction | [code:] 7B | [r1:] 7B")
    print("=" * 68)
    
    while True:
        try:
            user_input = input("\nAsk Vault (or 'exit'): ").strip()
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
            
            print("\n[1/2] Extracting facts from 136GB vault...", end=" ")
            top_link, extracted_data = search_offline_vault(clean_query)
            
            if extracted_data:
                print(f"Extracted context from:\n      -> {KIWIX_BASE}{top_link}")
            else:
                print("No direct text match; answering from internal weights.")
            
            print(f"[2/2] Streaming response [{selected_model}]:\n")
            query_llm(clean_query, model=selected_model, raw_context=extracted_data)
            
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
