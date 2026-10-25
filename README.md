# SparkVault: Offline Hybrid RAG Assistant

An offline engineering intelligence system combining local LLMs via Ollama with full-text search across 20 Kiwix ZIM databases (136+ GB).

## Architecture
- **Retrieval Engine:** `kiwix-serve` hosting offline Stack Exchange, Wikipedia, DevDocs, and LibreTexts on port `8088`.
- **Inference Engine:** Ollama running locally on port `11434`.
- **Models:**
  - `qwen2.5:3b` - High-speed writing and factual extraction.
  - `spark-coder:7b` - Optimized 4-thread technical code generation.
  - `deepseek-r1:7b` - Deep mathematical and logical reasoning.

## Requirements
- Python 3.10+
- `pip install requests beautifulsoup4`
- Ollama
- Kiwix Tools (`kiwix-serve`, `kiwix-manage`)
