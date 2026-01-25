"""
Academe - Multi-Agent Academic AI Assistant

Main entry point for the application.
Provides CLI interface for interacting with the multi-agent system.
"""

import sys
from academe.graph import process_query


def print_banner():
    """Print application banner"""
    banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║     ACADEME v0.1                                                  ║
║     Multi-Agent Academic AI Assistant                             ║
║                                                                   ║
║     Your AI tutor that adapts explanations to your level          ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_help():
    """Print help information"""
    help_text = """
What I can help you with:

  📚 CONCEPT EXPLANATIONS
     Get concepts explained at multiple levels:
     • Intuitive (simple analogies, no jargon)
     • Technical (mathematical rigor, formulas)
     
     Examples:
       → "What is gradient descent?"
       → "Explain Principal Component Analysis"
       → "Tell me about eigenvalues"

  💻 CODE GENERATION
     Get clean, educational Python implementations:
     • Well-commented code
     • Usage examples
     • Step-by-step explanations
     
     Examples:
       → "Implement gradient descent in NumPy"
       → "Show me PCA code from scratch"
       → "Write a function for k-means clustering"

Commands:
  help  - Show this help message
  demo  - Run demo mode with example queries
  quit  - Exit the application
"""
    print(help_text)


def demo_mode():
    """Run demo mode with predefined queries"""
    print("\n" + "═" * 70)
    print("📺 DEMO MODE - Example Queries")
    print("═" * 70 + "\n")
    
    demos = [
        {
            "query": "What is gradient descent?",
            "description": "Concept explanation with multi-level detail"
        },
        {
            "query": "Implement gradient descent in Python",
            "description": "Code generation with explanations"
        },
        {
            "query": "Explain Principal Component Analysis",
            "description": "Another concept explanation"
        }
    ]
    
    for i, demo in enumerate(demos, 1):
        print(f"\n{'─' * 70}")
        print(f"Demo {i}/{len(demos)}: {demo['description']}")
        print(f"Query: \"{demo['query']}\"")
        print('─' * 70 + "\n")
        
        try:
            result = process_query(demo['query'])
            print_result(result)
        except Exception as e:
            print(f"❌ Error: {str(e)}\n")
        
        if i < len(demos):
            response = input("\nContinue to next demo? (y/n): ").strip().lower()
            if response not in ['y', 'yes', '']:
                break
    
    print("\n✓ Demo complete!")


def print_result(result: dict, show_metadata: bool = False):
    """
    Pretty print the result from the workflow.
    
    Args:
        result: The result dictionary from process_query
        show_metadata: Whether to show routing metadata
    """
    if show_metadata:
        print("─" * 70)
        print(f"🤖 Agent: {result['agent_used'].replace('_', ' ').title()}")
        print(f"📍 Route: {result['route'].upper()}")
        print("─" * 70)
    
    print(result['response'])
    print()


def interactive_mode():
    """Interactive chat mode"""
    print("\n" + "═" * 70)
    print("💬 INTERACTIVE MODE")
    print("═" * 70)
    print("\nType 'help' for usage examples, 'demo' for demo mode, 'quit' to exit\n")
    
    query_count = 0
    
    while True:
        try:
            # Get user input
            question = input("🤔 Your question: ").strip()
            
            # Handle commands
            if not question:
                continue
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Thanks for using Academe! Happy learning!")
                break
            
            if question.lower() == 'help':
                print_help()
                continue
            
            if question.lower() == 'demo':
                demo_mode()
                continue
            
            # Process the query
            print()  # Blank line for spacing
            query_count += 1
            
            result = process_query(question)
            
            # Show metadata for first few queries to help user understand
            show_metadata = query_count <= 2
            print_result(result, show_metadata=show_metadata)
            
        except KeyboardInterrupt:
            print("\n\n👋 Thanks for using Academe! Happy learning!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try rephrasing your question.\n")


def main():
    """Main entry point"""
    print_banner()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command in ['help', '-h', '--help']:
            print_help()
            return
        
        elif command == 'demo':
            demo_mode()
            return
        
        elif command == 'version':
            print("Academe v0.1.0")
            return
        
        else:
            print(f"Unknown command: {command}")
            print("Try: python main.py help")
            return
    
    # Default: interactive mode
    interactive_mode()


if __name__ == "__main__":
    main()