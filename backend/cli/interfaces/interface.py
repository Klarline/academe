"""Rich CLI interface for Academe."""

import logging
from datetime import datetime
from typing import List, Optional

from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from core.models import (
    Conversation,
    ConversationSummary,
    ExplanationStyle,
    LearningGoal,
    LearningLevel,
    Message,
    RAGFallbackPreference,
    UserProfile,
)

logger = logging.getLogger(__name__)


class RichCLI:
    """Rich terminal interface for Academe."""

    def __init__(self):
        """Initialize Rich CLI."""
        self.console = Console()

    def show_welcome_banner(self) -> None:
        """Display welcome banner."""
        banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║                   A C A D E M E                       ║
    ║                                                       ║
    ║          Multi-Agent Academic AI Assistant            ║
    ║          Personalized Learning Experience             ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
        """
        self.console.print(
            Align.center(Text(banner, style="bold cyan")),
            highlight=False
        )

    def show_login_screen(self) -> tuple[str, str]:
        """
        Display login screen and collect credentials.

        Returns:
            Tuple of (email_or_username, password)
        """
        self.console.print("\n[bold cyan]Login to Academe[/bold cyan]\n")

        email_or_username = Prompt.ask(
            "[cyan]Email or Username[/cyan]"
        )

        password = Prompt.ask(
            "[cyan]Password[/cyan]",
            password=True
        )

        return email_or_username, password

    def show_registration_screen(self) -> tuple[str, str, str]:
        """
        Display registration screen and collect information.

        Returns:
            Tuple of (email, username, password)
        """
        self.console.print("\n[bold cyan]Create New Account[/bold cyan]\n")

        email = Prompt.ask(
            "[cyan]Email[/cyan]"
        )

        username = Prompt.ask(
            "[cyan]Username[/cyan]",
            default=email.split('@')[0]
        )

        while True:
            password = Prompt.ask(
                "[cyan]Password[/cyan]",
                password=True
            )

            confirm_password = Prompt.ask(
                "[cyan]Confirm Password[/cyan]",
                password=True
            )

            if password == confirm_password:
                break
            else:
                self.console.print("[red]Passwords don't match. Please try again.[/red]")

        return email, username, password

    def show_main_menu(self, user: UserProfile) -> str:
        """
        Display main menu and get user choice.

        Args:
            user: Current user profile

        Returns:
            Selected menu option
        """
        # Create header panel
        header_text = Text()
        header_text.append(f"User: {user.username}", style="bold yellow")
        header_text.append(" | ", style="dim")
        header_text.append(f"Level: {user.learning_level.value}", style="cyan")
        header_text.append(" | ", style="dim")
        header_text.append(f"Goal: {user.learning_goal.value}", style="green")

        header_panel = Panel(
            header_text,
            title="[bold]Academe Session[/bold]",
            border_style="cyan",
            padding=(0, 1),
        )
        self.console.print(header_panel)

        # Menu options
        self.console.print("\n[bold cyan]Main Menu:[/bold cyan]\n")
        self.console.print("  [yellow]1[/yellow] - Start New Conversation")
        self.console.print("  [yellow]2[/yellow] - Continue Previous Conversation")
        self.console.print("  [yellow]3[/yellow] - View Conversation History")
        self.console.print("  [yellow]4[/yellow] - Settings & Preferences")
        self.console.print("  [yellow]5[/yellow] - Export Data")
        self.console.print("  [yellow]6[/yellow] - Help")
        self.console.print("  [yellow]0[/yellow] - Logout\n")

        choice = Prompt.ask(
            "Your choice",
            choices=["0", "1", "2", "3", "4", "5", "6"],
            default="1"
        )

        return choice

    def show_settings_menu(self, user: UserProfile) -> Optional[dict]:
        """
        Display settings menu and collect preference updates.

        Args:
            user: Current user profile

        Returns:
            Dictionary of updated preferences or None if cancelled
        """
        self.console.print("\n[bold cyan]Settings & Preferences[/bold cyan]\n")

        # Display current settings
        current_table = Table(title="Current Settings", box=None)
        current_table.add_column("Setting", style="cyan")
        current_table.add_column("Current Value", style="yellow")

        current_table.add_row("Learning Level", user.learning_level.value)
        current_table.add_row("Learning Goal", user.learning_goal.value)
        current_table.add_row("Explanation Style", user.explanation_style.value)
        current_table.add_row("Document Mode", user.rag_fallback_preference.get_description())
        current_table.add_row("Include Math", "Yes" if user.include_math_formulas else "No")
        current_table.add_row("Include Visuals", "Yes" if user.include_visualizations else "No")
        current_table.add_row("Code Language", user.preferred_code_language)

        self.console.print(current_table)
        self.console.print()

        if not Confirm.ask("Would you like to update your preferences?", default=False):
            return None

        # Collect updates
        updates = {}

        # Update learning level
        if Confirm.ask("Update learning level?", default=False):
            self.console.print("\n[1] Beginner  [2] Intermediate  [3] Advanced")
            choice = Prompt.ask("Choice", choices=["1", "2", "3"])
            levels = {
                "1": LearningLevel.BEGINNER,
                "2": LearningLevel.INTERMEDIATE,
                "3": LearningLevel.ADVANCED,
            }
            updates["learning_level"] = levels[choice].value

        # Update learning goal
        if Confirm.ask("Update learning goal?", default=False):
            self.console.print("\n[1] Quick Review  [2] Deep Learning  [3] Exam Prep  [4] Research")
            choice = Prompt.ask("Choice", choices=["1", "2", "3", "4"])
            goals = {
                "1": LearningGoal.QUICK_REVIEW,
                "2": LearningGoal.DEEP_LEARNING,
                "3": LearningGoal.EXAM_PREP,
                "4": LearningGoal.RESEARCH,
            }
            updates["learning_goal"] = goals[choice].value

        # Update explanation style
        if Confirm.ask("Update explanation style?", default=False):
            self.console.print("\n[1] Intuitive  [2] Balanced  [3] Technical")
            choice = Prompt.ask("Choice", choices=["1", "2", "3"])
            styles = {
                "1": ExplanationStyle.INTUITIVE,
                "2": ExplanationStyle.BALANCED,
                "3": ExplanationStyle.TECHNICAL,
            }
            updates["explanation_style"] = styles[choice].value

        # Update RAG fallback preference
        if Confirm.ask("Update document mode?", default=False):
            self.console.print("\n[bold]Document Mode Options:[/bold]")
            self.console.print("  [1] Ask me each time what to do")
            self.console.print("  [2] Use general knowledge automatically")
            self.console.print("  [3] Only answer from my documents (strict)\n")
            
            choice = Prompt.ask("Choice", choices=["1", "2", "3"])
            preferences = {
                "1": RAGFallbackPreference.ALWAYS_ASK,
                "2": RAGFallbackPreference.PREFER_GENERAL,
                "3": RAGFallbackPreference.STRICT_DOCUMENTS,
            }
            updates["rag_fallback_preference"] = preferences[choice].value

        # Update math preference
        if Confirm.ask("Update math formulas preference?", default=False):
            updates["include_math_formulas"] = Confirm.ask(
                "Include mathematical formulas?",
                default=user.include_math_formulas
            )

        # Update visualizations preference
        if Confirm.ask("Update visualizations preference?", default=False):
            updates["include_visualizations"] = Confirm.ask(
                "Include ASCII visualizations?",
                default=user.include_visualizations
            )

        # Update code language
        if Confirm.ask("Update code language?", default=False):
            languages = ["python", "javascript", "java", "cpp", "go", "rust"]
            self.console.print("\nAvailable languages:")
            for i, lang in enumerate(languages, 1):
                current = " (current)" if lang == user.preferred_code_language else ""
                self.console.print(f"  [{i}] {lang}{current}")
            
            lang_choice = Prompt.ask(
                "Choice",
                choices=[str(i) for i in range(1, len(languages) + 1)]
            )
            updates["preferred_code_language"] = languages[int(lang_choice) - 1]

        return updates if updates else None

    def display_conversation_history(
        self,
        conversations: List[ConversationSummary]
    ) -> Optional[str]:
        """
        Display conversation history and let user select one.

        Args:
            conversations: List of conversation summaries

        Returns:
            Selected conversation ID or None
        """
        if not conversations:
            self.console.print("[yellow]No conversations found.[/yellow]")
            return None

        # Create conversations table
        table = Table(
            title="Conversation History",
            show_lines=True,
            header_style="bold cyan"
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="white")
        table.add_column("Messages", justify="right", style="yellow")
        table.add_column("Last Activity", style="green")
        table.add_column("Status", justify="center")

        for idx, conv in enumerate(conversations, 1):
            status = "Archived" if conv.is_archived else "Active"
            last_activity = conv.last_message_at or conv.created_at
            date_str = last_activity.strftime("%Y-%m-%d %H:%M")

            table.add_row(
                str(idx),
                conv.title[:50] + "..." if len(conv.title) > 50 else conv.title,
                str(conv.message_count),
                date_str,
                status
            )

        self.console.print(table)
        self.console.print()

        # Let user select
        choice = Prompt.ask(
            "Select conversation # (or 0 to cancel)",
            choices=[str(i) for i in range(len(conversations) + 1)],
            default="0"
        )

        if choice == "0":
            return None

        return conversations[int(choice) - 1].id

    def display_message(
        self,
        message: Message,
        show_metadata: bool = False
    ) -> None:
        """
        Display a single message.

        Args:
            message: Message to display
            show_metadata: Whether to show metadata
        """
        # Format role
        if message.role == "user":
            role_style = "bold cyan"
            role_label = "USER"
        elif message.role == "assistant":
            role_style = "bold green"
            role_label = "ASSISTANT"
        else:
            role_style = "dim"
            role_label = message.role.upper()

        # Create message panel
        content = Text(message.content, style="white")

        # Add metadata if requested
        if show_metadata and message.role == "assistant":
            metadata = []
            if message.agent_used:
                metadata.append(f"Agent: {message.agent_used}")
            if message.route:
                metadata.append(f"Route: {message.route}")
            if message.processing_time_ms:
                metadata.append(f"Time: {message.processing_time_ms}ms")

            if metadata:
                content.append("\n\n", style="dim")
                content.append(" | ".join(metadata), style="dim italic")

        panel = Panel(
            content,
            title=f"{role_label}",
            title_align="left",
            border_style=role_style,
            padding=(0, 1),
        )

        self.console.print(panel)
        self.console.print()

    def display_conversation(
        self,
        conversation: Conversation,
        messages: List[Message]
    ) -> None:
        """
        Display a complete conversation.

        Args:
            conversation: Conversation object
            messages: List of messages
        """
        # Display header
        header = Panel(
            f"[bold]{conversation.title}[/bold]\n"
            f"[dim]Created: {conversation.created_at.strftime('%Y-%m-%d %H:%M')} | "
            f"Messages: {len(messages)}[/dim]",
            border_style="cyan"
        )
        self.console.print(header)
        self.console.print()

        # Display messages
        for message in messages:
            self.display_message(message, show_metadata=False)

    def show_spinner(self, text: str = "Processing...") -> Live:
        """
        Show a spinner with text.

        Args:
            text: Text to display with spinner

        Returns:
            Live display object (use as context manager)
        """
        spinner = Spinner("dots", text=f"[cyan]{text}[/cyan]")
        return Live(spinner, console=self.console, refresh_per_second=10)

    def show_error(self, message: str) -> None:
        """
        Display an error message.

        Args:
            message: Error message to display
        """
        error_panel = Panel(
            f"[red]Error: {message}[/red]",
            border_style="red",
            padding=(0, 1),
        )
        self.console.print(error_panel)

    def show_success(self, message: str) -> None:
        """
        Display a success message.

        Args:
            message: Success message to display
        """
        success_panel = Panel(
            f"[green]Success: {message}[/green]",
            border_style="green",
            padding=(0, 1),
        )
        self.console.print(success_panel)

    def show_info(self, message: str) -> None:
        """
        Display an info message.

        Args:
            message: Info message to display
        """
        info_panel = Panel(
            f"[cyan]Info: {message}[/cyan]",
            border_style="cyan",
            padding=(0, 1),
        )
        self.console.print(info_panel)

    def show_warning(self, message: str) -> None:
        """
        Display a warning message.

        Args:
            message: Warning message to display
        """
        warning_panel = Panel(
            f"[yellow]Warning: {message}[/yellow]",
            border_style="yellow",
            padding=(0, 1),
        )
        self.console.print(warning_panel)

    def show_help(self) -> None:
        """Display help information."""
        help_text = """
[bold cyan]Academe Commands:[/bold cyan]

During conversation:
  [yellow]help[/yellow]     - Show this help message
  [yellow]settings[/yellow] - Update your preferences
  [yellow]history[/yellow]  - View conversation history
  [yellow]export[/yellow]   - Export conversation to JSON
  [yellow]new[/yellow]      - Start new conversation
  [yellow]quit[/yellow]     - Exit Academe

[bold cyan]Features:[/bold cyan]
  - Personalized responses based on your learning preferences
  - Document-based Q&A with RAG (upload PDFs, notes, textbooks)
  - Practice problem generation from your materials
  - Multi-agent system (Concept Explainer, Code Helper, Research Agent)
  - Conversation history automatically saved

[bold cyan]Document Mode:[/bold cyan]
You can control what happens when documents don't have answers:
  - Ask each time: Get prompted for choices
  - Use general knowledge: Automatically answer from AI knowledge
  - Only documents: Strictly answer from your materials only

Change this anytime in Settings (option 4 from main menu).

[bold cyan]Tips:[/bold cyan]
  - Upload course materials for best personalized results
  - Update settings to change explanation style
  - Export conversations for offline review
  - Use Research mode for document-specific questions
  - Use Chat mode for general explanations
        """
        self.console.print(help_text)

    def confirm_action(self, message: str, default: bool = False) -> bool:
        """
        Ask for confirmation.

        Args:
            message: Confirmation message
            default: Default choice

        Returns:
            User's choice
        """
        return Confirm.ask(message, default=default)

    def get_text_input(
        self,
        prompt: str,
        default: Optional[str] = None,
        password: bool = False
    ) -> str:
        """
        Get text input from user.

        Args:
            prompt: Input prompt
            default: Default value
            password: Hide input for passwords

        Returns:
            User input
        """
        return Prompt.ask(prompt, default=default, password=password)

    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        self.console.clear()

    def display_settings_summary(self, user: UserProfile) -> None:
        """
        Display a summary of current user settings.

        Args:
            user: User profile
        """
        summary_panel = Panel(
            f"""[bold cyan]Your Current Settings:[/bold cyan]

[cyan]Learning Preferences:[/cyan]
  Level: [yellow]{user.learning_level.value}[/yellow]
  Goal: [yellow]{user.learning_goal.value}[/yellow]
  Style: [yellow]{user.explanation_style.value}[/yellow]

[cyan]Document Mode:[/cyan]
  [yellow]{user.rag_fallback_preference.get_description()}[/yellow]

[cyan]Content Preferences:[/cyan]
  Math Formulas: [yellow]{'Yes' if user.include_math_formulas else 'No'}[/yellow]
  Visualizations: [yellow]{'Yes' if user.include_visualizations else 'No'}[/yellow]
  Code Language: [yellow]{user.preferred_code_language}[/yellow]

[dim]Change these in Settings (option 4 from main menu)[/dim]""",
            title="Settings Overview",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(summary_panel)

    def show_rag_preference_info(self, preference: RAGFallbackPreference) -> None:
        """
        Show information about RAG preference.

        Args:
            preference: Current RAG preference
        """
        descriptions = {
            RAGFallbackPreference.ALWAYS_ASK: (
                "When documents don't have answers, I'll offer you choices:\n"
                "  - Answer from general knowledge\n"
                "  - Upload more documents\n"
                "  - Rephrase your question"
            ),
            RAGFallbackPreference.PREFER_GENERAL: (
                "When documents don't have answers, I'll automatically\n"
                "provide answers from general AI knowledge.\n"
                "Great for mixing course materials with general learning."
            ),
            RAGFallbackPreference.STRICT_DOCUMENTS: (
                "I will ONLY answer from your uploaded documents.\n"
                "I'll never use general knowledge.\n"
                "Great for studying specific course materials only."
            )
        }

        info_panel = Panel(
            f"[bold]Current Document Mode:[/bold] [yellow]{preference.get_description()}[/yellow]\n\n"
            f"{descriptions[preference]}\n\n"
            f"[dim]Change this in Settings (option 4 from main menu)[/dim]",
            title="Document Mode",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(info_panel)