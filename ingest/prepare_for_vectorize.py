"""
prepare_for_vectorize.py — Convert chunks.jsonl to Vectorize-compatible NDJSON.

Vectorize expects: {"id": "...", "values": [...], "metadata": {...}}
Our chunks.jsonl has: {"id": "...", "text": "...", "embedding": [...], "metadata": {...}}

We need to rename `embedding` to `values` and keep text inside metadata so we can 
return it with search results.
"""

import json
from pathlib import Path

INPUT_FILE = Path(__file__).parent / "chunks.jsonl"
OUTPUT_FILE = Path(__file__).parent / "vectorize_upload.ndjson"

# Vectorize ID constraint: must be ≤ 64 bytes, only safe chars
# Our IDs from chunk_docs.py may be too long or have weird chars — sanitize

def sanitize_id(raw_id: str, fallback_index: int) -> str:
    """Vectorize IDs: ≤64 chars, alphanumeric + underscore + hyphen."""
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in raw_id)
    if len(safe) > 60:
        # Truncate but keep uniqueness with index suffix
        safe = safe[:55] + f"_{fallback_index}"
    return safe


def main():
    print(f"Reading from {INPUT_FILE}...")
    
    seen_ids = set()
    written = 0
    duplicates = 0
    
    with INPUT_FILE.open("r", encoding="utf-8") as fin, \
         OUTPUT_FILE.open("w", encoding="utf-8") as fout:
        
        for i, line in enumerate(fin):
            chunk = json.loads(line)
            
            # Sanitize ID
            chunk_id = sanitize_id(chunk["id"], i)
            
            # Handle duplicates (rare but possible after sanitization)
            if chunk_id in seen_ids:
                chunk_id = f"{chunk_id}_{i}"
                duplicates += 1
            seen_ids.add(chunk_id)
            
            # Build Vectorize record
            vectorize_record = {
                "id": chunk_id,
                "values": chunk["embedding"],
                "metadata": {
                    # Include text in metadata so we can return it with results
                    # (Vectorize won't store text in vectors themselves)
                    "text": chunk["text"][:9500],  # Vectorize metadata limit: 10KB per record
                    "source_url": chunk["metadata"]["source_url"],
                    "slug": chunk["metadata"]["slug"],
                    "h1": chunk["metadata"].get("h1") or "",
                    "h2": chunk["metadata"].get("h2") or "",
                    "h3": chunk["metadata"].get("h3") or "",
                }
            }
            
            fout.write(json.dumps(vectorize_record, ensure_ascii=False) + "\n")
            written += 1
    
    print(f"\nDone!")
    print(f"  Records written: {written}")
    if duplicates > 0:
        print(f"  Duplicate IDs after sanitization (auto-renamed): {duplicates}")
    print(f"  Output: {OUTPUT_FILE}")
    print(f"  File size: {OUTPUT_FILE.stat().st_size / (1024 * 1024):.1f} MB")


if __name__ == "__main__":
    main() 