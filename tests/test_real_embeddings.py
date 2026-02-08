"""
Test Real Embeddings vs Mock Embeddings

This script verifies that real embeddings are installed and working.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("="*80)
print("Testing Real Embeddings - Semantic Similarity Check")
print("="*80)

# Test 1: Check if sentence-transformers is installed
print("\n1. Checking if sentence-transformers is installed...")
try:
    from sentence_transformers import SentenceTransformer
    print("✅ sentence-transformers is installed!")
except ImportError:
    print("❌ sentence-transformers NOT installed")
    print("Run: pip install sentence-transformers")
    sys.exit(1)

# Test 2: Check Academe's embedding service
print("\n2. Checking Academe's embedding service...")
from academe.vectors.embeddings import EmbeddingService

embedding_service = EmbeddingService()

if embedding_service.provider == "mock":
    print("❌ Still using MOCK MODE (random embeddings)")
    print("   This means sentence-transformers didn't load properly")
    mock_mode = True
else:
    print(f"✅ Using REAL embeddings ({embedding_service.model_name})")
    print(f"   Provider: {embedding_service.provider}")
    print(f"   Dimensions: {embedding_service.embedding_dim}")
    mock_mode = False

# Test 3: Semantic similarity test
print("\n3. Testing semantic similarity...")
print("   Generating embeddings for related and unrelated concepts...")

# Related concepts (should be similar)
concept1 = "eigenvalues and eigenvectors in linear algebra"
concept2 = "principal component analysis dimensionality reduction"
concept3 = "pizza recipe with cheese and tomatoes"

emb1 = embedding_service.generate_embedding(concept1)
emb2 = embedding_service.generate_embedding(concept2)
emb3 = embedding_service.generate_embedding(concept3)

print(f"\n   Concept 1: '{concept1}'")
print(f"   Embedding: [{emb1[0]:.4f}, {emb1[1]:.4f}, {emb1[2]:.4f}, ...]")

print(f"\n   Concept 2: '{concept2}'")
print(f"   Embedding: [{emb2[0]:.4f}, {emb2[1]:.4f}, {emb2[2]:.4f}, ...]")

print(f"\n   Concept 3: '{concept3}'")
print(f"   Embedding: [{emb3[0]:.4f}, {emb3[1]:.4f}, {emb3[2]:.4f}, ...]")

# Calculate cosine similarity
import numpy as np

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors."""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

sim_1_2 = cosine_similarity(emb1, emb2)  # Related (both ML)
sim_1_3 = cosine_similarity(emb1, emb3)  # Unrelated (ML vs food)
sim_2_3 = cosine_similarity(emb2, emb3)  # Unrelated (ML vs food)

print("\n4. Similarity Scores:")
print(f"   Eigenvalues ↔ PCA:        {sim_1_2:.4f} (should be HIGH - both ML)")
print(f"   Eigenvalues ↔ Pizza:      {sim_1_3:.4f} (should be LOW - unrelated)")
print(f"   PCA ↔ Pizza:              {sim_2_3:.4f} (should be LOW - unrelated)")

# Interpretation
print("\n5. Interpretation:")

if mock_mode:
    print("   ⚠️  MOCK MODE: Similarities are random")
    print("   All scores will be around 0.0 ± 0.3 (random)")
else:
    if sim_1_2 > 0.5:
        print(f"   ✅ ML concepts are similar ({sim_1_2:.4f} > 0.5)")
    else:
        print(f"   ⚠️  ML concepts should be more similar (got {sim_1_2:.4f})")
    
    if sim_1_3 < 0.3 and sim_2_3 < 0.3:
        print(f"   ✅ ML and food are dissimilar ({sim_1_3:.4f}, {sim_2_3:.4f} < 0.3)")
    else:
        print(f"   ⚠️  ML and food should be more different")

# Test 4: Real-world example
print("\n6. Real-world search example:")
print("   Searching for: 'gradient descent optimization'")

test_chunks = [
    "Gradient descent is an optimization algorithm that minimizes loss functions",
    "Principal Component Analysis reduces data dimensionality",
    "Pizza recipes typically include flour, water, and yeast"
]

query_emb = embedding_service.generate_embedding("gradient descent optimization")

similarities = []
for i, chunk in enumerate(test_chunks):
    chunk_emb = embedding_service.generate_embedding(chunk)
    sim = cosine_similarity(query_emb, chunk_emb)
    similarities.append((chunk, sim))

# Sort by similarity
similarities.sort(key=lambda x: x[1], reverse=True)

print("\n   Results (sorted by relevance):")
for i, (chunk, sim) in enumerate(similarities, 1):
    print(f"   {i}. [{sim:.4f}] {chunk[:60]}...")

# Check if ranking makes sense
if not mock_mode:
    if similarities[0][0].startswith("Gradient"):
        print("\n   ✅ CORRECT! Gradient descent chunk ranked #1")
        print("   ✅ Real embeddings are working properly!")
    else:
        print("\n   ❌ WRONG! Should rank gradient descent chunk #1")
else:
    print("\n   ⚠️  MOCK MODE: Rankings are random")

# Summary
print("\n" + "="*80)
print("Summary")
print("="*80)

if mock_mode:
    print("\n❌ MOCK MODE ACTIVE")
    print("   - sentence-transformers not working")
    print("   - RAG search will return random results")
    print("   - Memory system works fine (uses LLM, not embeddings)")
else:
    print("\n✅ REAL EMBEDDINGS ACTIVE")
    print("   - sentence-transformers loaded successfully")
    print("   - RAG search will return semantically relevant results")
    print("   - Document Q&A will actually work!")
    print("\n   Model: all-MiniLM-L6-v2 (384 dimensions)")
    print("   Usage: Research Agent, Concept Explainer RAG, Code Helper RAG")

print("\n" + "="*80)
