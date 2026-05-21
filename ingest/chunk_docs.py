"""
chunk_docs.py — Parse markdown files and split into chunks for RAG.

Usage:
    python chunk_docs.py

Output:
    chunks.json — list of chunks with text + metadata
"""

import json
import re
from pathlib import Path
from tqdm import tqdm

# Configuration
DOCS_DIR = Path(__file__).parent / "cache" / "laravel-docs"
OUTPUT_FILE = Path(__file__).parent / "chunks.json"
BASE_URL = "https://laravel.com/docs/13.x"

# Chunking parameters
CHUNK_SIZE = 500       # ~500 words per chunk (roughly ~650 tokens)
CHUNK_OVERLAP = 50     # overlap between consecutive chunks to preserve context


def extract_sections(markdown_text: str) -> list[dict]:
    """
    Split markdown into sections by headings.
    Each section keeps track of its heading and parent heading.
    """
    sections = []
    current_h1 = None
    current_h2 = None
    current_h3 = None
    current_content = []
    
    for line in markdown_text.split("\n"):
        h1_match = re.match(r"^# (.+)", line)
        h2_match = re.match(r"^## (.+)", line)
        h3_match = re.match(r"^### (.+)", line)
        
        if h1_match:
            # Save previous section if it has content
            if current_content:
                sections.append({
                    "h1": current_h1,
                    "h2": current_h2,
                    "h3": current_h3,
                    "text": "\n".join(current_content).strip()
                })
            current_h1 = h1_match.group(1).strip()
            current_h2 = None
            current_h3 = None
            current_content = []
        elif h2_match:
            if current_content:
                sections.append({
                    "h1": current_h1,
                    "h2": current_h2,
                    "h3": current_h3,
                    "text": "\n".join(current_content).strip()
                })
            current_h2 = h2_match.group(1).strip()
            current_h3 = None
            current_content = []
        elif h3_match:
            if current_content:
                sections.append({
                    "h1": current_h1,
                    "h2": current_h2,
                    "h3": current_h3,
                    "text": "\n".join(current_content).strip()
                })
            current_h3 = h3_match.group(1).strip()
            current_content = []
        else:
            current_content.append(line)
    
    # Don't forget the last section
    if current_content:
        sections.append({
            "h1": current_h1,
            "h2": current_h2,
            "h3": current_h3,
            "text": "\n".join(current_content).strip()
        })
    
    # Filter out empty sections
    return [s for s in sections if s["text"]]


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks of approximately `size` words."""
    words = text.split()
    if len(words) <= size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += size - overlap
    
    return chunks


def process_file(file_path: Path) -> list[dict]:
    """Process a single markdown file into chunks with metadata."""
    content = file_path.read_text(encoding="utf-8")
    
    # Filename without .md = URL slug
    slug = file_path.stem
    source_url = f"{BASE_URL}/{slug}"
    
    sections = extract_sections(content)
    chunks = []
    
    for section in sections:
        section_chunks = chunk_text(section["text"])
        for i, chunk_text_content in enumerate(section_chunks):
            chunks.append({
                "id": f"{slug}__{section['h2'] or section['h1'] or 'root'}__{i}".replace(" ", "_"),
                "text": chunk_text_content,
                "metadata": {
                    "file": file_path.name,
                    "slug": slug,
                    "h1": section["h1"],
                    "h2": section["h2"],
                    "h3": section["h3"],
                    "source_url": source_url,
                }
            })
    
    return chunks


def main():
    md_files = sorted(DOCS_DIR.glob("*.md"))
    print(f"Processing {len(md_files)} markdown files...")
    
    all_chunks = []
    for file_path in tqdm(md_files):
        try:
            file_chunks = process_file(file_path)
            all_chunks.extend(file_chunks)
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")
    
    print(f"\nGenerated {len(all_chunks)} chunks total.")
    print(f"Average chunks per file: {len(all_chunks) / len(md_files):.1f}")
    
    # Save to JSON
    OUTPUT_FILE.write_text(json.dumps(all_chunks, indent=2, ensure_ascii=False))
    print(f"\nSaved to {OUTPUT_FILE}")
    
    # Show sample chunk
    if all_chunks:
        sample = all_chunks[len(all_chunks) // 2]  # middle chunk
        print(f"\n--- Sample chunk ---")
        print(f"ID: {sample['id']}")
        print(f"Source: {sample['metadata']['source_url']}")
        print(f"Section: H1={sample['metadata']['h1']}, H2={sample['metadata']['h2']}")
        print(f"Text (first 300 chars):\n{sample['text'][:300]}...")


if __name__ == "__main__":
    main()