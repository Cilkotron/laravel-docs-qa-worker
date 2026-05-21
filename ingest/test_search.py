"""
test_search.py — Test Vectorize search by embedding a query and finding similar chunks.

Usage:
    python ingest/test_search.py "your search query"
"""

import subprocess
import sys
import json
import tempfile
import os
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-base-en-v1.5"


def query_vectorize(query_text: str, top_k: int = 3):
    print(f"\nQuery: {query_text}\n")
    
    # Embed the query
    print("Embedding query...")
    model = SentenceTransformer(MODEL_NAME)
    embedding = model.encode(query_text, normalize_embeddings=True).tolist()
    
    print(f"Querying Vectorize for top {top_k} results...\n")
    
    # Use shell with xargs to expand the vector values correctly
    # We write embedding to a JSON file, then use jq + xargs to pass as args
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(embedding, f)
        temp_path = f.name
    
    try:
        # Build shell command that uses jq + xargs to expand vector
        shell_cmd = (
            f"npx wrangler vectorize query laravel-docs "
            f"--top-k {top_k} "
            f"--return-metadata all "
            f"--vector $(jq -r '.[]' {temp_path} | xargs)"
        )
        
        result = subprocess.run(
            shell_cmd,
            shell=True,
            capture_output=True,
            text=True,
        )
        
        print(result.stdout)
        if result.returncode != 0:
            print("STDERR:", result.stderr, file=sys.stderr)
    finally:
        os.unlink(temp_path)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "How do I define a route in Laravel?"
    query_vectorize(query)