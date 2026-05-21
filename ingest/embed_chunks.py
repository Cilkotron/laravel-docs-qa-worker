"""
embed_chunks.py — Generate embeddings for chunks using sentence-transformers.

Usage:
    python embed_chunks.py

Input:
    chunks.json — list of chunks with text + metadata

Output:
    chunks.jsonl — same chunks, but with `embedding` field added (one per line)
"""

import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Configuration
INPUT_FILE = Path(__file__).parent / "chunks.json"
OUTPUT_FILE = Path(__file__).parent / "chunks.jsonl"
MODEL_NAME = "BAAI/bge-base-en-v1.5"  # 768-dim embedding model
BATCH_SIZE = 32  # process 32 chunks at a time (good for CPU)


def main():
    # Load chunks
    print(f"Loading chunks from {INPUT_FILE}...")
    chunks = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    print(f"Loaded {len(chunks)} chunks.")
    
    # Load model
    print(f"\nLoading embedding model: {MODEL_NAME}")
    print("(First run will download ~440 MB model — subsequent runs use cached version)")
    model = SentenceTransformer(MODEL_NAME)
    print(f"Model loaded. Embedding dimension: {model.get_sentence_embedding_dimension()}")
    
    # Extract texts for batch processing
    texts = [chunk["text"] for chunk in chunks]
    
    # Generate embeddings (in batches with progress bar)
    print(f"\nGenerating embeddings (batch size: {BATCH_SIZE})...")
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,  # important for cosine similarity in Vectorize
    )
    
    # Attach embeddings to chunks
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding.tolist()  # numpy array → Python list
    
    # Write JSONL (one chunk per line — required by Vectorize bulk upload)
    print(f"\nWriting to {OUTPUT_FILE}...")
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    
    # Verification
    file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"\nDone!")
    print(f"  Output file: {OUTPUT_FILE}")
    print(f"  File size: {file_size_mb:.1f} MB")
    print(f"  Chunks: {len(chunks)}")
    print(f"  Embedding dimension: {len(chunks[0]['embedding'])}")
    
    # Sanity check on a sample
    print(f"\n--- Sample chunk (with embedding) ---")
    sample = chunks[0]
    print(f"ID: {sample['id']}")
    print(f"Text preview: {sample['text'][:150]}...")
    print(f"Embedding length: {len(sample['embedding'])}")
    print(f"First 5 embedding values: {sample['embedding'][:5]}")


if __name__ == "__main__":
    main()