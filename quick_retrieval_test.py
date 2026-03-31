#!/usr/bin/env python
"""Quick Retrieval Test - Direct FAISS index test"""
import sys
sys.path.insert(0, '.')

import pickle
import numpy as np
from pathlib import Path

print("=" * 80)
print("QUICK RETRIEVAL TEST - Checking FAISS Index")
print("=" * 80)

try:
    # Check if FAISS index files exist
    index_path = Path("./data/vector_index/chunks.index")
    metadata_path = Path("./data/vector_index/chunks_metadata.pkl")
    
    print(f"\n[1/4] Checking index files...")
    print(f"  ✓ chunks.index exists: {index_path.exists()} (size: {index_path.stat().st_size / (1024*1024):.2f} MB)" if index_path.exists() else "  ✗ chunks.index NOT found")
    print(f"  ✓ chunks_metadata.pkl exists: {metadata_path.exists()} (size: {metadata_path.stat().st_size / 1024:.2f} KB)" if metadata_path.exists() else "  ✗ metadata NOT found")
    
    if not index_path.exists() or not metadata_path.exists():
        print("\n✗ FAISS index files not found!")
        sys.exit(1)
    
    # Load FAISS index
    print(f"\n[2/4] Loading FAISS index...")
    import faiss
    index = faiss.read_index(str(index_path))
    print(f"  ✓ FAISS index loaded")
    print(f"  ✓ Total vectors: {index.ntotal}")
    print(f"  ✓ Index dimension: {index.d}D")
    
    # Load metadata
    print(f"\n[3/4] Loading metadata...")
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)
    print(f"  ✓ Metadata loaded")
    print(f"  ✓ Total entries in metadata: {len(metadata)}")
    
    # Test retrieval with random vector
    print(f"\n[4/4] Testing retrieval...")
    test_vector = np.random.randn(1, index.d).astype(np.float32)
    distances, indices = index.search(test_vector, k=5)
    
    print(f"  ✓ Retrieved {len(indices[0])} results")
    print(f"  ✓ Top distance: {distances[0][0]:.4f}")
    print(f"  ✓ Retrieved chunk IDs: {indices[0][:3]}...")
    
    print("\n" + "=" * 80)
    print("✓ RETRIEVAL TEST PASSED - FAISS Index is working!")
    print("=" * 80)
    print("\nSystem Status:")
    print(f"  • Embeddings in FAISS: {index.ntotal}")
    print(f"  • Index dimension: {index.d}D")
    print(f"  • Index file: {index_path.stat().st_size / (1024*1024):.2f} MB")
    print(f"\nReady for Q&A queries!")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
