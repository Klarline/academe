"""
Interactive demo of the Academe multi-agent system.

This is your main demonstration script showing the complete system in action.
"""

from academe.graph import process_query


def print_header():
    """Print welcome header"""
    print("\n" + "=" * 70)
    print("🎓 Academe v0.1 - Multi-Agent Academic AI Assistant")
    print("=" * 70)
    print("\nI can help you with:")
    print("  📚 Concept Explanations (intuitive + technical)")
    print("  💻 Code Generation (Python with NumPy)")
    print("\nType 'quit' to exit")
    print("=" * 70 + "\n")


def print_result(result: dict):
    """Pretty print the workflow result"""
    print("\n" + "─" * 70)
    print(f"🤖 Agent: {result['agent_used'].replace('_', ' ').title()}")
    print(f"📍 Route: {result['route'].upper()}")
    print("─" * 70)
    print(result['response'])
    print("─" * 70 + "\n")


def demo_mode():
    """Run predefined demo queries"""
    print_header()
    print("📺 DEMO MODE - Showing example queries...\n")
    
    demo_queries = [
        "What is gradient descent?",
        "Show me how to implement gradient descent in Python",
        "Explain Principal Component Analysis",
        "Write code for k-means clustering",
    ]
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n{'=' * 70}")
        print(f"Demo Query {i}/{len(demo_queries)}: {query}")
        print('=' * 70 + "\n")
        
        result = process_query(query)
        print_result(result)
        
        if i < len(demo_queries):
            input("Press Enter for next demo...")


def interactive_mode():
    """Interactive chat mode"""
    print_header()
    
    while True:
        try:
            question = input("🤔 Your question: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Thanks for using Academe!")
                break
            
            if not question:
                continue
            
            print()  # Blank line for spacing
            
            # Process through workflow
            result = process_query(question)
            
            # Display result
            print_result(result)
        
        except KeyboardInterrupt:
            print("\n\n👋 Thanks for using Academe!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")


def main():
    """Main entry point"""
    print("\nSelect mode:")
    print("1. Demo Mode (see example queries)")
    print("2. Interactive Mode (ask your own questions)")
    
    choice = input("\nChoice (1/2): ").strip()
    
    if choice == "1":
        demo_mode()
    elif choice == "2":
        interactive_mode()
    else:
        print("Invalid choice. Running demo mode...")
        demo_mode()


if __name__ == "__main__":
    main()