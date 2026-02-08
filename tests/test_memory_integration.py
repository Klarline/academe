"""
Test Memory Integration 

This script tests that memory context is properly built and passed to agents.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from academe.database import init_database
from academe.database import UserRepository
from academe.database.progress_repository import ProgressRepository
from academe.memory.context_manager import ContextManager
from academe.models import ConceptMastery

print("="*80)
print("Testing Memory Integration - v0.4")
print("="*80)

# Initialize database
print("\n1. Initializing database...")
init_database()
print("✅ Database initialized")

# Get test user
print("\n2. Getting test user...")
user_repo = UserRepository()

# Use the known test account
try:
    test_user = user_repo.get_user_by_email("test@test.com")
    
    if not test_user:
        print("❌ User test@test.com not found.")
        print("\nPlease run 'python main.py' first and verify the account exists.")
        sys.exit(1)
    
    print(f"✅ Using user: {test_user.username} (ID: {test_user.id})")
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nPlease verify the user account test@test.com exists.")
    sys.exit(1)

# Create some test progress data
print("\n3. Creating test learning progress...")
progress_repo = ProgressRepository()

test_concepts = [
    ("eigenvalues", 0.35, 10, 4),  # Weak area
    ("PCA", 0.45, 8, 4),           # Learning
    ("gradient_descent", 0.75, 15, 12),  # Proficient
]

for concept, mastery, attempted, correct in test_concepts:
    # Track interaction
    progress_repo.track_concept_interaction(
        user_id=test_user.id,
        concept=concept,
        interaction_type="practice",
        details={"correct": correct > 0, "time_spent": 5}
    )
    
    # Update progress
    progress = progress_repo.get_concept_progress(test_user.id, concept)
    if progress:
        progress.questions_attempted = attempted
        progress.questions_correct = correct
        progress.mastery_score = mastery
        progress.mastery_level = progress.calculate_mastery_level()
        
        progress_repo.update_concept_progress(
            user_id=test_user.id,
            concept=concept,
            updates=progress.dict(exclude={"id"})
        )

print(f"✅ Created progress for {len(test_concepts)} concepts")

# Test memory context building
print("\n4. Testing memory context building...")
context_manager = ContextManager()

test_query = "What is gradient descent?"
memory_context = context_manager.build_agent_context(
    user=test_user,
    query=test_query,
    conversation_id="test_conv_123"
)

print(f"\n📊 Memory Context Built:")
print(f"   - Query: {test_query}")

if "relevant_concepts" in memory_context:
    print(f"   - Relevant Concepts: {memory_context['relevant_concepts']}")
else:
    print("   - Relevant Concepts: (None - LLM filtering may not have run)")

if "weak_areas" in memory_context:
    print(f"   - Weak Areas: {memory_context['weak_areas']}")
else:
    print("   - Weak Areas: (None)")

if "learning_progress" in memory_context:
    recent = memory_context["learning_progress"].get("recent_concepts", [])
    print(f"   - Recently Studied: {[c['concept'] for c in recent]}")

if memory_context.get("is_followup"):
    print("   - Is Follow-up: Yes")
else:
    print("   - Is Follow-up: No")

# Test with LLM filtering
print("\n5. Testing LLM concept filtering...")
all_concepts = ["eigenvalues", "PCA", "gradient_descent"]
test_query2 = "Explain how eigenvalues work"

relevant = context_manager._filter_relevant_concepts(test_query2, all_concepts)
print(f"   - Query: {test_query2}")
print(f"   - All concepts: {all_concepts}")
print(f"   - Relevant concepts (LLM filtered): {relevant}")

if "eigenvalues" in relevant:
    print("   ✅ LLM correctly identified eigenvalues as relevant")
else:
    print("   ⚠️  LLM may not have filtered correctly")

# Test full workflow integration
print("\n6. Testing full workflow with memory...")
from academe.graph.workflow import process_with_langgraph

try:
    final_state = process_with_langgraph(
        question="Explain gradient descent in simple terms",
        user_id=test_user.id,
        conversation_id="test_conv_123",
        user_profile=test_user.dict() if hasattr(test_user, 'dict') else test_user.model_dump()
    )
    
    print("✅ Workflow completed successfully")
    print(f"   - Agent used: {final_state.get('agent_used')}")
    print(f"   - Route: {final_state.get('route')}")
    print(f"   - Has memory context: {'memory_context' in final_state and final_state['memory_context'] is not None}")
    
    if final_state.get('response'):
        response_preview = final_state['response'][:200]
        print(f"   - Response preview: {response_preview}...")
    
except Exception as e:
    print(f"❌ Workflow failed: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "="*80)
print("Test Summary")
print("="*80)
print("\n✅ Tests completed!")
print("\nWhat was tested:")
print("  1. Database initialization")
print("  2. User retrieval")
print("  3. Learning progress creation")
print("  4. Memory context building")
print("  5. LLM concept filtering")
print("  6. Full workflow with memory")
print("\nNext steps:")
print("  - Run the app: python main.py")
print("  - Ask questions and watch memory adapt")
print("  - Check Celery worker logs for memory updates")
print("\n" + "="*80)
