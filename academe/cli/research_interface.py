"""Research and practice interface for Academe with RAG preference support."""

import logging
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.markdown import Markdown

from academe.agents.research_agent import ResearchAgent
from academe.agents.practice_generator import PracticeGenerator
from academe.models import UserProfile, RAGFallbackPreference
from academe.rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)


class ResearchInterface:
    """Interface for research and practice features with RAG preference support."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize research interface."""
        self.console = console or Console()
        self.research_agent = ResearchAgent()
        self.practice_generator = PracticeGenerator()
        self.rag_pipeline = RAGPipeline()
    
    def show_research_menu(self) -> str:
        """
        Show research menu.

        Returns:
            Selected option
        """
        self.console.print("\n[bold cyan]Research & Practice[/bold cyan]\n")

        self.console.print("  [yellow]1[/yellow] - Ask Question from Documents")
        self.console.print("  [yellow]2[/yellow] - Research Topic")
        self.console.print("  [yellow]3[/yellow] - Generate Practice Questions")
        self.console.print("  [yellow]4[/yellow] - Create Flashcards")
        self.console.print("  [yellow]5[/yellow] - Compare Concepts")
        self.console.print("  [yellow]6[/yellow] - Find Examples")
        self.console.print("  [yellow]0[/yellow] - Back to Main Menu\n")

        choice = Prompt.ask(
            "Your choice",
            choices=["0", "1", "2", "3", "4", "5", "6"],
            default="1"
        )

        return choice
    
    def ask_question(self, user: UserProfile) -> None:
        """Ask a question about documents."""
        self.console.print("\n[bold cyan]Ask a Question[/bold cyan]\n")
        
        question = Prompt.ask("Your question")
        
        with self.console.status("Searching documents..."):
            answer, sources = self.rag_pipeline.query_with_context(
                query=question,
                user=user,
                top_k=5,
                use_reranking=True
            )
        
        if sources and len(sources) > 0:
            # Success - show answer with sources
            self._display_answer_with_sources(answer, sources)
        else:
            # No context - handle based on preference
            self._handle_no_context_with_preference(question, user, answer)

    def _display_answer_with_sources(self, answer: str, sources: list) -> None:
        """Display successful RAG answer with sources."""
        self.console.print("\n[bold green]Answer:[/bold green]\n")
        self.console.print(Markdown(answer))
        
        if sources:
            self.console.print("\n[bold cyan]Sources:[/bold cyan]\n")
            for i, source in enumerate(sources[:5], 1):
                source_text = f"{i}. {source.document.title or source.document.original_filename}"
                if source.chunk.page_number:
                    source_text += f" (p. {source.chunk.page_number})"
                source_text += f" - Relevance: {source.score:.2f}"
                self.console.print(f"  {source_text}")
    
    def _handle_no_context_with_preference(
        self,
        question: str,
        user: UserProfile,
        answer: str
    ) -> None:
        """Handle no-context scenario based on user's preference."""
        
        self.console.print(f"\n[yellow]No relevant content found in your documents.[/yellow]\n")
        
        preference = user.rag_fallback_preference
        
        if preference == RAGFallbackPreference.ALWAYS_ASK:
            self._handle_fallback_interactive(question, user)
        elif preference == RAGFallbackPreference.PREFER_GENERAL:
            self._handle_fallback_automatic(question, user)
        else:  # STRICT_DOCUMENTS
            self._handle_fallback_strict(question, user)

    def _handle_fallback_interactive(self, question: str, user: UserProfile) -> None:
        """Interactive fallback - ask user what to do."""
        self.console.print("[bold]What would you like to do?[/bold]\n")
        self.console.print("  [cyan]1[/cyan] - Upload documents")
        self.console.print("  [cyan]2[/cyan] - Rephrase question")
        self.console.print("  [cyan]0[/cyan] - Cancel\n")
        
        choice = Prompt.ask("Your choice", choices=["0", "1", "2"], default="1")
        
        if choice == "1":
            self._redirect_to_upload(user)
        elif choice == "2":
            self._rephrase_question(user)

    def _handle_fallback_automatic(self, question: str, user: UserProfile) -> None:
        """Automatic fallback - use general knowledge."""
        self.console.print("[dim]Documents don't have this info. Answering from general knowledge...[/dim]\n")
        # The answer was already generated by RAG pipeline fallback, just show note
        self.console.print("[dim]Note: This answer is from general knowledge, not your documents.[/dim]")

    def _handle_fallback_strict(self, question: str, user: UserProfile) -> None:
        """Strict fallback - only offer document options."""
        self.console.print("[bold]Your preference is to only use documents.[/bold]\n")
        self.console.print("  [cyan]1[/cyan] - Upload documents")
        self.console.print("  [cyan]2[/cyan] - Change preference\n")
        
        choice = Prompt.ask("Your choice", choices=["1", "2"], default="1")
        
        if choice == "1":
            self._redirect_to_upload(user)
        elif choice == "2":
            self._change_rag_preference(user)
    
    def _answer_from_general_knowledge(
        self,
        question: str,
        user: UserProfile
    ) -> None:
        """Generate answer from LLM's general knowledge."""
        self.console.print("\n[dim]Generating answer from general knowledge...[/dim]\n")
        
        try:
            with self.console.status("Thinking..."):
                answer = self.rag_pipeline.generate_fallback_answer(question, user)
            
            # Display answer
            self.console.print("[bold green]Answer (from general knowledge):[/bold green]\n")
            self.console.print(Markdown(answer))
            
            # Show disclaimer
            self.console.print("\n[dim]Note: This answer is from general knowledge, not your documents.[/dim]")
            
        except Exception as e:
            self.console.print(f"\n[red]Failed to generate answer: {e}[/red]")

    def _redirect_to_upload(self, user: UserProfile) -> None:
        """Redirect to document upload."""
        self.console.print("\n[cyan]Redirecting to document upload...[/cyan]\n")
        
        # Import here to avoid circular import
        from academe.cli.document_interface import DocumentInterface
        doc_interface = DocumentInterface(self.console)
        
        # Upload document
        success = doc_interface.upload_document(user.id)
        
        if success:
            self.console.print("\n[green]Document uploaded! You can now ask questions about it.[/green]")
        else:
            self.console.print("\n[yellow]Upload cancelled or failed.[/yellow]")

    def _rephrase_question(self, user: UserProfile) -> None:
        """Let user rephrase their question."""
        self.console.print("\n[cyan]Let's try rephrasing your question:[/cyan]\n")
        
        # Show tips
        tips = Panel(
            """Tips for better results:
- Be more specific about the topic
- Use keywords from your documents
- Ask about specific concepts or sections
- Try "What does my document say about..."
""",
            title="Rephrasing Tips",
            border_style="cyan"
        )
        self.console.print(tips)
        
        # Get new question
        new_question = Prompt.ask("\nYour rephrased question")
        
        if not new_question:
            return
        
        # Try again with new question
        with self.console.status("Searching with new question..."):
            result = self.rag_pipeline.query_with_context(
                query=new_question,
                user=user,
                top_k=5,
                use_reranking=True
            )
        
        answer, sources = result
        if sources:
            self._display_answer_with_sources(result)
        elif result.needs_fallback:
            self.console.print(f"\n[yellow]{result.message}[/yellow]")
            # Offer one more chance
            if Confirm.ask("\nTry different options?", default=False):
                self._handle_fallback_with_preference(new_question, user, result)
        else:
            self.console.print(f"\n[red]Error: {result.message}[/red]")

    def _view_documents(self, user: UserProfile) -> None:
        """Show user's documents."""
        from academe.cli.document_interface import DocumentInterface
        doc_interface = DocumentInterface(self.console)
        doc_interface.view_documents(user.id)

    def _change_rag_preference(self, user: UserProfile) -> None:
        """Allow user to change RAG fallback preference."""
        self.console.print("\n[bold cyan]Change Document Mode Preference[/bold cyan]\n")
        
        self.console.print("Current: [green]{}[/green]\n".format(
            user.rag_fallback_preference.get_description()
        ))
        
        self.console.print("  [cyan]1[/cyan] - Ask me each time")
        self.console.print("  [cyan]2[/cyan] - Use general knowledge automatically")
        self.console.print("  [cyan]3[/cyan] - Only use my documents (strict)\n")
        
        choice = Prompt.ask("New preference", choices=["1", "2", "3"])
        
        preference_map = {
            "1": RAGFallbackPreference.ALWAYS_ASK,
            "2": RAGFallbackPreference.PREFER_GENERAL,
            "3": RAGFallbackPreference.STRICT_DOCUMENTS
        }
        
        new_preference = preference_map[choice]
        
        if new_preference != user.rag_fallback_preference:
            user.rag_fallback_preference = new_preference
            
            # Update in database
            from academe.database import UserRepository
            user_repo = UserRepository()
            user_repo.update_user_preferences(
                user.id,
                {"rag_fallback_preference": new_preference.value}
            )
            
            self.console.print(f"\n[green]Updated to: {new_preference.get_description()}[/green]\n")
        else:
            self.console.print("\n[dim]No change made.[/dim]\n")
    
    def research_topic(self, user: UserProfile) -> None:
        """
        Research a topic comprehensively.

        Args:
            user: User profile
        """
        self.console.print("\n[bold cyan]Research Topic[/bold cyan]\n")

        topic = Prompt.ask("Topic to research")

        depth_options = ["quick", "standard", "deep"]
        self.console.print("\nResearch depth:")
        for i, option in enumerate(depth_options, 1):
            self.console.print(f"  [{i}] {option.capitalize()}")

        depth_choice = Prompt.ask(
            "Select depth",
            choices=["1", "2", "3"],
            default="2"
        )
        depth = depth_options[int(depth_choice) - 1]

        # Research with progress
        with self.console.status(f"Researching {topic}..."):
            research = self.research_agent.research_topic(
                topic=topic,
                user=user,
                depth=depth
            )

        # Display research
        self.console.print("\n")
        self.console.print(Markdown(research))

    def generate_practice(self, user: UserProfile) -> None:
        """
        Generate practice questions.

        Args:
            user: User profile
        """
        self.console.print("\n[bold cyan]Generate Practice Questions[/bold cyan]\n")

        topic = Prompt.ask("Topic for practice")

        num_questions = Prompt.ask(
            "Number of questions",
            default="5"
        )

        # Question types
        self.console.print("\nQuestion types to include:")
        self.console.print("  [1] Multiple Choice")
        self.console.print("  [2] Short Answer")
        self.console.print("  [3] Explanation")
        self.console.print("  [4] Code (if applicable)")
        self.console.print("  [5] All types")

        type_choice = Prompt.ask(
            "Select types (comma-separated)",
            default="5"
        )

        if "5" in type_choice:
            question_types = ["mcq", "short", "explain", "code"]
        else:
            type_map = {
                "1": "mcq",
                "2": "short",
                "3": "explain",
                "4": "code"
            }
            question_types = [
                type_map[c.strip()]
                for c in type_choice.split(",")
                if c.strip() in type_map
            ]

        # Generate practice set
        with self.console.status("Generating practice questions..."):
            practice_set = self.practice_generator.generate_practice_set(
                topic=topic,
                user=user,
                num_questions=int(num_questions),
                question_types=question_types
            )

        # Display questions
        if "error" in practice_set:
            self.console.print(f"[red]{practice_set['error']}[/red]")
            return

        self.console.print(f"\n[bold green]Practice Set: {practice_set['topic']}[/bold green]\n")
        self.console.print(f"Difficulty: {practice_set['difficulty']}")
        self.console.print(f"Total questions: {practice_set['total_questions']}\n")

        for i, question in enumerate(practice_set["questions"], 1):
            self._display_question(i, question)
        
        # Ask if user wants to generate more
        self.console.print()
        more = Prompt.ask(
            "Generate more questions?",
            choices=["y", "n"],
            default="n"
        )
        
        if more.lower() == "y":
            self.generate_practice(user)

    def create_flashcards(self, user: UserProfile) -> None:
        """
        Create flashcards for study.

        Args:
            user: User profile
        """
        self.console.print("\n[bold cyan]Create Flashcards[/bold cyan]\n")

        topic = Prompt.ask("Topic for flashcards")

        num_cards = Prompt.ask(
            "Number of flashcards",
            default="10"
        )

        # Generate flashcards
        with self.console.status("Creating flashcards..."):
            flashcards = self.practice_generator.generate_flashcards(
                topic=topic,
                user=user,
                num_cards=int(num_cards)
            )

        if not flashcards:
            self.console.print("[red]No flashcards could be generated.[/red]")
            return

        # Display flashcards
        self.console.print(f"\n[bold green]Flashcards: {topic}[/bold green]\n")

        for i, card in enumerate(flashcards, 1):
            panel = Panel(
                f"[bold cyan]Front:[/bold cyan] {card.get('front', 'N/A')}\n\n"
                f"[bold green]Back:[/bold green] {card.get('back', 'N/A')}",
                title=f"Flashcard {i}",
                border_style="cyan"
            )
            self.console.print(panel)

    def compare_concepts(self, user: UserProfile) -> None:
        """
        Compare two concepts.

        Args:
            user: User profile
        """
        self.console.print("\n[bold cyan]Compare Concepts[/bold cyan]\n")

        concept1 = Prompt.ask("First concept")
        concept2 = Prompt.ask("Second concept")

        # Generate comparison
        with self.console.status(f"Comparing {concept1} vs {concept2}..."):
            comparison = self.research_agent.compare_concepts(
                concept1=concept1,
                concept2=concept2,
                user=user
            )

        # Display comparison
        self.console.print("\n[bold green]Comparison:[/bold green]\n")
        self.console.print(Markdown(comparison))

    def find_examples(self, user: UserProfile) -> None:
        """
        Find examples of a concept.

        Args:
            user: User profile
        """
        self.console.print("\n[bold cyan]Find Examples[/bold cyan]\n")

        concept = Prompt.ask("Concept to find examples for")

        num_examples = Prompt.ask(
            "Number of examples",
            default="3"
        )

        # Find examples
        with self.console.status(f"Finding examples of {concept}..."):
            examples = self.research_agent.find_examples(
                concept=concept,
                user=user,
                num_examples=int(num_examples)
            )

        # Display examples
        self.console.print("\n[bold green]Examples:[/bold green]\n")
        self.console.print(Markdown(examples))

    def _display_question(self, num: int, question: dict) -> None:
        """Display a practice question."""
        q_type = question.get("type", "unknown")
        q_text = question.get("question", "")
        q_answer = question.get("answer", "")
        q_explanation = question.get("explanation", "")
        q_options = question.get("options", [])

        panel_content = f"[bold]Question {num} ({q_type}):[/bold]\n{q_text}"

        # Display MCQ options if present
        if q_type == "mcq" and q_options:
            panel_content += "\n\n[bold yellow]Options:[/bold yellow]"
            for i, option in enumerate(q_options, 1):
                # Format as A, B, C, D
                letter = chr(64 + i)  # 65 is 'A'
                panel_content += f"\n  {letter}) {option}"

        if q_answer:
            panel_content += f"\n\n[bold green]Answer:[/bold green]\n{q_answer}"

        if q_explanation:
            panel_content += f"\n\n[bold cyan]Explanation:[/bold cyan]\n{q_explanation}"

        panel = Panel(
            panel_content,
            border_style="cyan"
        )

        self.console.print(panel)
    
    def _answer_from_general_knowledge(self, question: str, user: UserProfile) -> None:
        """Generate answer from LLM's general knowledge."""
        self.console.print("\n[dim]Generating answer from general knowledge...[/dim]\n")
        
        try:
            # Use concept explainer for general knowledge
            from academe.agents.concept_explainer import explain_concept_with_context
            
            with self.console.status("Thinking..."):
                answer = explain_concept_with_context(
                    question=question,
                    user_profile=user,
                    context=None
                )
            
            self.console.print("[bold green]Answer (from general knowledge):[/bold green]\n")
            self.console.print(Markdown(answer))
            self.console.print("\n[dim]Note: This answer is from general knowledge, not your documents.[/dim]")
            
        except Exception as e:
            self.console.print(f"\n[red]Failed to generate answer: {e}[/red]")

    def _redirect_to_upload(self, user: UserProfile) -> None:
        """Redirect to document upload."""
        self.console.print("\n[cyan]Redirecting to document upload...[/cyan]\n")
        
        from academe.cli.document_interface import DocumentInterface
        doc_interface = DocumentInterface(self.console)
        
        success = doc_interface.upload_document(user.id)
        
        if success:
            self.console.print("\n[green]Document uploaded! You can now ask questions about it.[/green]")
        else:
            self.console.print("\n[yellow]Upload cancelled or failed.[/yellow]")

    def _rephrase_question(self, user: UserProfile) -> None:
        """Let user rephrase their question."""
        self.console.print("\n[cyan]Let's try rephrasing your question:[/cyan]\n")
        
        tips = Panel(
            """Tips for better results:
- Be more specific about the topic
- Use keywords from your documents
- Ask about specific concepts or sections
- Try "What does my document say about..."
""",
            title="Rephrasing Tips",
            border_style="cyan"
        )
        self.console.print(tips)
        
        new_question = Prompt.ask("\nYour rephrased question")
        
        if not new_question:
            return
        
        with self.console.status("Searching with new question..."):
            answer, sources = self.rag_pipeline.query_with_context(
                query=new_question,
                user=user,
                top_k=5,
                use_reranking=True
            )
        
        if sources:
            self._display_answer_with_sources(answer, sources)
        else:
            self.console.print("\n[yellow]Still no relevant content found.[/yellow]")
            if Confirm.ask("\nTry different options?", default=False):
                self._handle_no_context_with_preference(new_question, user, answer)

    def _view_documents(self, user: UserProfile) -> None:
        """Show user's documents."""
        from academe.cli.document_interface import DocumentInterface
        doc_interface = DocumentInterface(self.console)
        doc_interface.view_documents(user.id)

    def _change_rag_preference(self, user: UserProfile) -> None:
        """Allow user to change RAG fallback preference."""
        self.console.print("\n[bold cyan]Change Document Mode Preference[/bold cyan]\n")
        
        self.console.print("Current: [green]{}[/green]\n".format(
            user.rag_fallback_preference.get_description()
        ))
        
        self.console.print("  [cyan]1[/cyan] - Ask me each time")
        self.console.print("  [cyan]2[/cyan] - Use general knowledge automatically")
        self.console.print("  [cyan]3[/cyan] - Only use my documents (strict)\n")
        
        choice = Prompt.ask("New preference", choices=["1", "2", "3"])
        
        preference_map = {
            "1": RAGFallbackPreference.ALWAYS_ASK,
            "2": RAGFallbackPreference.PREFER_GENERAL,
            "3": RAGFallbackPreference.STRICT_DOCUMENTS
        }
        
        new_preference = preference_map[choice]
        
        if new_preference != user.rag_fallback_preference:
            user.rag_fallback_preference = new_preference
            
            from academe.database import UserRepository
            user_repo = UserRepository()
            user_repo.update_user(
                user.id,
                {"rag_fallback_preference": new_preference.value}
            )
            
            self.console.print(f"\n[green]Updated to: {new_preference.get_description()}[/green]\n")
        else:
            self.console.print("\n[dim]No change made.[/dim]\n")

