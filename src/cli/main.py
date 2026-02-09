#!/usr/bin/env python3
"""
Academe - Academic AI Assistant with Memory & Progress Tracking

This version includes:
- Multi-user authentication
- Personalized responses
- Document processing and RAG
- Research agent for document Q&A 
- Practice problem generation
- Learning progress tracking
- Memory context across sessions
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from core.auth import AuthService
from cli.interfaces import RichCLI, Session
from cli.interfaces.document_interface import DocumentInterface
from cli.interfaces.research_interface import ResearchInterface
from core.config.settings import get_settings, validate_api_keys
from core.database import get_database, init_database
from core.documents import DocumentManager
from core.graph.workflow import process_with_langgraph
from core.models import Message
from core.onboarding import OnboardingFlow
from core.database import ConversationRepository
from core.agents.router import route_query_structured, get_agent_description
from core.agents.research_agent import ResearchAgent
from cli.interfaces.progress_interface import ProgressInterface
from core.database.progress_repository import ProgressRepository
from core.memory import ContextManager
from core.utils.task_helpers import queue_memory_update, extract_concepts_from_query, is_celery_available

# Version
VERSION = "0.4.0" 


class AcademeCLI:
    """Main CLI application for Academe."""

    def __init__(self):
        """Initialize the CLI application."""
        self.cli = RichCLI()
        self.session = Session()
        self.auth_service = AuthService()
        self.onboarding = OnboardingFlow()
        self.conv_repo = ConversationRepository()
        self.doc_interface = DocumentInterface(self.cli.console)
        self.research_interface = ResearchInterface(self.cli.console)
        self.doc_manager = DocumentManager()
        self.research_agent = ResearchAgent()
        
        # Initialize database connection FIRST
        try:
            init_database()
        except Exception as e:
            self.cli.show_error(f"Failed to connect to database: {e}")
            self.cli.show_info("Make sure MongoDB is running: docker-compose up -d")
            sys.exit(1)
        
        try:
            self.progress_interface = ProgressInterface(self.cli.console)
            db = get_database()
            self.progress_repo = ProgressRepository(database=db)
            self.context_manager = ContextManager(
                progress_repo=self.progress_repo,
                conversation_repo=self.conv_repo
            )
            self.current_session_id = None
        except Exception as e:
            self.cli.console.print(f"[yellow]Warning: v0.4 features initialization failed: {e}[/yellow]")
            self.progress_interface = None
            self.progress_repo = None
            self.context_manager = None
            self.current_session_id = None

    def run(self):
        """Main application loop."""
        # Show welcome banner
        self.cli.show_welcome_banner()

        # Check for existing session
        if self.session.is_authenticated():
            self.cli.show_success(f"Welcome back, {self.session.user.username}!")
            self._start_study_session()
            self._show_progress_summary()
        else:
            # Login or register
            if not self._auth_flow():
                return

            self._start_study_session()

        # Check for onboarding
        if self.onboarding.should_show_onboarding(self.session.user):
            self.session.user = self.onboarding.run_onboarding(self.session.user)
            self.session.update_user_preferences({
                "has_completed_onboarding": True
            })

        # Main loop
        try:
            self._main_loop()
        finally:
            self._end_study_session()

    def _start_study_session(self):
        """Start a new study session for tracking."""
        try:
            self.current_session_id = self.progress_repo.start_study_session(
                user_id=self.session.user.id,
                session_type="general"
            )
            self.cli.console.print(
                f"[dim]Study session started at {datetime.now().strftime('%H:%M')}[/dim]"
            )
        except Exception:
            pass  # Session tracking is optional

    def _end_study_session(self):
        """End the current study session."""
        if hasattr(self, 'current_session_id') and self.current_session_id:
            try:
                self.progress_repo.end_study_session(
                    session_id=self.current_session_id
                )
                self.cli.console.print("[dim]Study session ended. Great work!  📚[/dim]")
            except Exception:
                pass

    def _show_progress_summary(self):
        """Show brief progress summary on login."""
        try:
            dashboard = self.progress_interface._build_dashboard_data(self.session.user.id)
            
            if not dashboard.get('memory_available'):
                return
            
            if dashboard.get('total_concepts_studied', 0) > 0:
                self.cli.console.print("\n[bold cyan]📊 Your Progress Summary:[/bold cyan]")
                
                streak = dashboard.get('study_streak_days', 0)
                if streak > 0:
                    self.cli.console.print(f"  🔥 Study streak: {streak} days")
                
                mastered = dashboard.get('concepts_mastered', 0)
                total = dashboard.get('total_concepts_studied', 0)
                self.cli.console.print(f"  📚 Concepts mastered: {mastered}/{total}")
                
                recs = dashboard.get('recommendations', [])
                if recs and len(recs) > 0:
                    self.cli.console.print(f"  💡 Recommended focus: {recs[0]['concept']}")
                
                self.cli.console.print("")
        except Exception:
            pass  # Progress display is optional

    def _auth_flow(self) -> bool:
        """Handle authentication flow."""
        while True:
            self.cli.console.print("\n[cyan]1[/cyan] - Login")
            self.cli.console.print("[cyan]2[/cyan] - Register")
            self.cli.console.print("[cyan]0[/cyan] - Exit\n")

            choice = self.cli.get_text_input("Your choice", default="1")

            if choice == "0":
                return False
            elif choice == "1":
                if self._login():
                    return True
            elif choice == "2":
                if self._register():
                    return True

    def _login(self) -> bool:
        """Handle login process."""
        email_or_username, password = self.cli.show_login_screen()

        if self.session.login(email_or_username, password):
            self.cli.show_success(f"Welcome back, {self.session.user.username}!")
            return True
        else:
            self.cli.show_error("Invalid credentials. Please try again.")
            return False

    def _register(self) -> bool:
        """Handle registration process."""
        email, username, password = self.cli.show_registration_screen()

        try:
            user = self.auth_service.register_user(email, username, password)
            if user:
                self.session.login(email, password)
                self.cli.show_success(f"Account created! Welcome, {username}!")
                return True
            else:
                self.cli.show_error("Registration failed. Please try again.")
                return False
        except ValueError as e:
            self.cli.show_error(str(e))
            return False

    def _main_loop(self):
        """Main menu loop with features."""
        while True:
            # Build menu dynamically based on features available
            self.cli.console.print("\n[bold cyan]Main Menu:[/bold cyan]\n")
            self.cli.console.print("  [yellow]1[/yellow] - Chat (AI Assistant)")
            self.cli.console.print("  [yellow]2[/yellow] - Research (Document Q&A)")
            self.cli.console.print("  [yellow]3[/yellow] - Documents (Upload/Manage)")
            self.cli.console.print("  [yellow]4[/yellow] - Practice (Generate Exercises)")
            

            self.cli.console.print("  [yellow]5[/yellow] - Progress (Learning Dashboard)")
            self.cli.console.print("  [yellow]6[/yellow] - History (Past Conversations)")
            self.cli.console.print("  [yellow]7[/yellow] - Settings")
            self.cli.console.print("  [yellow]8[/yellow] - Help")
            valid_choices = ["0", "1", "2", "3", "4", "5", "6", "7", "8"]
            
            self.cli.console.print("  [yellow]0[/yellow] - Logout\n")

            choice = self.cli.get_text_input("Your choice", default="1")

            if choice not in valid_choices:
                continue

            if choice == "0":  # Logout
                self.session.logout()
                self.cli.show_info("Logged out successfully. Goodbye!")
                break
            elif choice == "1":  # Chat
                self._chat_mode()
            elif choice == "2":  # Research
                self._research_mode()
            elif choice == "3":  # Documents
                self._document_management()
            elif choice == "4":  # Practice
                self._practice_mode()
            elif choice == "5":  # Progress or History
                self._progress_dashboard()
            elif choice == "6":  # History or Settings
                self._view_history()
            elif choice == "7":  # Settings or Help
                self._update_settings()
            elif choice == "8":  # Help
                self._show_help()

    def _chat_mode(self):
        """Chat mode with optional memory."""
        mode_desc = "AI assistant with memory" 
        
        self.cli.console.print(f"\n[bold cyan]Chat Mode[/bold cyan]")
        self.cli.console.print(f"[dim]{mode_desc}[/dim]\n")

        self.session.create_new_conversation("Chat Session")
        conversation = self.session.current_conversation
        
        try:
            self.context_manager.initialize_session_context(
                user_id=self.session.user.id,
                conversation_id=conversation.id
            )
        except Exception:
            pass

        while True:
            question = self.cli.get_text_input("[cyan]You[/cyan]")

            if not question or question.lower() in ["quit", "exit", "q", "0"]:
                break
            elif question.lower() == "help":
                self.cli.show_help()
                continue

            # Save user message
            user_message = Message(
                conversation_id=conversation.id,
                user_id=self.session.user.id,
                role="user",
                content=question
            )
            self.conv_repo.add_message(user_message)

            # Process with optional memory
            with self.cli.show_spinner("Thinking..."):
                final_state = process_with_langgraph(
                    question=question,
                    user_id=self.session.user.id,
                    conversation_id=conversation.id,
                    user_profile=self.session.user.model_dump() if hasattr(self.session.user, 'model_dump') else {}
                )

                response = final_state.get("response", "No response generated")
                metadata = {
                    "agent_used": final_state.get("agent_used"),
                    "route": final_state.get("route"),
                    "confidence": final_state.get("routing_confidence"),
                }

            # Save and display response
            assistant_message = Message(
                conversation_id=conversation.id,
                user_id=self.session.user.id,
                role="assistant",
                content=response,
                agent_used=metadata.get("agent_used"),
                route=metadata.get("route")
            )
            self.conv_repo.add_message(assistant_message)
            
            # Update memory in background (Celery)
            try:
                concepts = extract_concepts_from_query(question)
                queue_memory_update(
                    user_id=self.session.user.id,
                    conversation_id=conversation.id,
                    interaction={
                        "query": question,
                        "concepts": concepts,
                        "agent_used": metadata.get("agent_used"),
                        "type": "question"
                    },
                    async_mode=True  # Use Celery if available, fallback to sync
                )
            except Exception as e:
                # Don't fail the main flow if memory update fails
                self.cli.console.print(f"[dim yellow]Note: Memory update queued in background[/dim yellow]")
            
            # Show context indicators
            if metadata.get('is_followup'):
                self.cli.console.print("[dim italic]↳ Follow-up detected[/dim italic]")

            self.cli.display_message(assistant_message, show_metadata=True)

    def _research_mode(self):
        """Research mode using documents."""
        docs = self.doc_manager.get_user_documents(self.session.user.id)
        if not docs:
            self.cli.show_info(
                "No documents found! Upload documents first to use research features."
            )
            if self.cli.confirm_action("Would you like to upload a document now?"):
                self._document_management()
            return

        while True:
            choice = self.research_interface.show_research_menu()

            if choice == "0":
                break
            elif choice == "1":
                self.research_interface.ask_question(self.session.user)
            elif choice == "2":
                self.research_interface.research_topic(self.session.user)
            elif choice == "3":
                self.research_interface.generate_practice(self.session.user)
            elif choice == "4":
                self.research_interface.create_flashcards(self.session.user)
            elif choice == "5":
                self.research_interface.compare_concepts(self.session.user)
            elif choice == "6":
                self.research_interface.find_examples(self.session.user)

    def _document_management(self):
        """Document management interface."""
        while True:
            choice = self.doc_interface.show_document_menu(self.session.user.id)

            if choice == "0":
                break
            elif choice == "1":
                self.doc_interface.upload_document(self.session.user.id)
            elif choice == "2":
                self.doc_interface.view_documents(self.session.user.id)
            elif choice == "3":
                self.doc_interface.search_documents(self.session.user.id)
            elif choice == "4":
                self.doc_interface.delete_document(self.session.user.id)

    def _practice_mode(self):
        """Practice mode for generating exercises."""
        self.research_interface.generate_practice(self.session.user)

    def _progress_dashboard(self):
        """Show learning progress dashboard."""
        if self.progress_interface is None:
            self.cli.show_info("Progress tracking not available.")
            return
    
        while True:
            choice = self.progress_interface.show_progress_menu()

            if choice == "0":
                break
            elif choice == "1":
                self.progress_interface.show_dashboard(self.session.user)
            elif choice == "2":
                self.progress_interface.show_detailed_progress(self.session.user)
            elif choice == "3":
                self.progress_interface.show_study_sessions(self.session.user)
            elif choice == "4":
                self.progress_interface.export_progress(self.session.user)

    def _view_history(self):
        """View conversation history."""
        conversations = self.conv_repo.get_user_conversations(
            self.session.user.id,
            include_archived=False,
            limit=50
        )

        if not conversations:
            self.cli.show_info("No conversations found.")
            return

        conv_id = self.cli.display_conversation_history(conversations)
        if conv_id:
            messages = self.conv_repo.get_conversation_messages(conv_id)
            conversation = self.conv_repo.get_conversation(conv_id)
            self.cli.display_conversation(conversation, messages)

    def _update_settings(self):
        """Update user settings."""
        updates = self.cli.show_settings_menu(self.session.user)
        if updates:
            success = self.session.update_user_preferences(updates)
            if success:
                self.cli.show_success("Settings updated successfully!")
            else:
                self.cli.show_error("Failed to update settings.")

    def _show_help(self):
        """Show help information."""
        version_text = "With Memory & Progress Tracking"
        
        help_text = f"""
[bold cyan]Academe {version_text}[/bold cyan]

[bold]Core Features:[/bold]
- 📚 Document Upload: Process PDFs, text files, and markdown
- 🔍 Research Mode: Ask questions about your documents
- 💡 Personalized Learning: Responses adapted to your level
- ✏️ Practice Generation: Create quizzes and flashcards
- 🤖 Multi-Agent System: Specialized agents for different tasks
- 💾 Conversation History: All chats are saved

[bold]Memory Features:[/bold]
- 🧠 Memory Context: Remembers your learning journey
- 📊 Progress Tracking: Tracks mastery levels
- 📈 Learning Dashboard: Visualize progress
- 💡 Smart Recommendations: Personalized study suggestions
- 🎯 Weak Area Detection: Identifies concepts needing practice
- 🔥 Study Streaks: Tracks consecutive learning days
"""
        
        help_text += """
[bold]Modes:[/bold]
- Chat: AI assistant with personalized responses
- Research: Document-based Q&A with citations
- Documents: Upload and manage study materials
- Practice: Generate exercises from documents

        
• Progress: View learning dashboard and analytics
        
[bold]Tips:[/bold]
- Upload your textbooks and notes for best results
- Use Research mode for document-specific questions
- Use Chat mode for general explanations

• Check your progress dashboard regularly\n"
"""
        
        self.cli.console.print(help_text)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()

        if arg in ["-h", "--help", "help"]:
            print(f"""
Academe v{VERSION} - Academic AI Assistant

Usage:
  python main.py        Start interactive mode
  python main.py help   Show this help message
  python main.py version Show version

Features:
  • Multi-user authentication
  • Document processing and RAG
  • Personalized explanations
  • Practice problem generation
  • Research from documents
  • Learning progress tracking"
  • Memory context across sessions""")
            return

        elif arg in ["-v", "--version", "version"]:
            print(f"Academe v{VERSION}")
            return

    # Validate API keys
    try:
        validate_api_keys()
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nPlease set up your .env file with required API keys.")
        sys.exit(1)

    # Run the application
    try:
        app = AcademeCLI()
        app.run()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()