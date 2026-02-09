"""Onboarding flow for new users in Academe."""

import logging
from typing import Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from core.database import UserRepository
from core.models import (
    ExplanationStyle,
    LearningGoal,
    LearningLevel,
    RAGFallbackPreference,
    UserProfile
)

logger = logging.getLogger(__name__)


class OnboardingFlow:
    """Interactive onboarding flow for new users."""

    def __init__(self):
        """Initialize onboarding flow."""
        self.console = Console()
        self.user_repo = UserRepository()

    def should_show_onboarding(self, user: UserProfile) -> bool:
        """
        Check if onboarding should be shown for a user.

        Args:
            user: User profile

        Returns:
            True if onboarding should be shown
        """
        return not user.has_completed_onboarding

    def run_onboarding(self, user: UserProfile) -> UserProfile:
        """
        Run the complete onboarding flow.

        Args:
            user: User profile to update

        Returns:
            Updated user profile with preferences
        """
        self.console.clear()
        self._show_welcome(user.username)

        # Collect preferences
        preferences = {}

        # Step 1: Learning Level
        preferences["learning_level"] = self._ask_learning_level()

        # Step 2: Learning Goal
        preferences["learning_goal"] = self._ask_learning_goal()

        # Step 3: Explanation Style
        preferences["explanation_style"] = self._ask_explanation_style()

        # Step 4: RAG Fallback Preference (NEW)
        preferences["rag_fallback_preference"] = self._ask_rag_preference()
        preferences["has_seen_rag_explanation"] = True

        # Step 5: Additional Preferences
        additional_prefs = self._ask_additional_preferences()
        preferences.update(additional_prefs)

        # Step 6: Show Summary and Confirm
        if self._confirm_preferences(preferences):
            # Save preferences
            success = self.save_preferences(user.id, preferences)
            if success:
                # Update user object
                for key, value in preferences.items():
                    setattr(user, key, value)
                user.has_completed_onboarding = True

                self._show_completion_message()
                return user
            else:
                self.console.print(
                    "[red]Failed to save preferences. Please try again.[/red]"
                )
                return user
        else:
            # Restart onboarding
            return self.run_onboarding(user)

    def _show_welcome(self, username: str) -> None:
        """Show welcome message."""
        welcome_text = Text()
        welcome_text.append("Welcome to ", style="bold white")
        welcome_text.append("Academe", style="bold cyan")
        welcome_text.append(", ", style="bold white")
        welcome_text.append(username, style="bold yellow")
        welcome_text.append("!", style="bold white")

        panel = Panel(
            "[white]Let's personalize your learning experience.\n\n"
            "I'll ask you a few questions to understand your learning preferences "
            "so I can provide explanations and code examples that match your needs.[/white]",
            title=welcome_text,
            border_style="cyan",
            padding=(1, 2),
        )
        self.console.print(panel)
        self.console.print()

    def _ask_learning_level(self) -> LearningLevel:
        """Ask user for their learning level."""
        self.console.print("[bold cyan]Step 1/5: What's your current learning level?[/bold cyan]\n")

        # Create options table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Choice", style="yellow")
        table.add_column("Level", style="cyan")
        table.add_column("Description")

        levels = [
            ("1", "Beginner", "New to ML concepts, need foundational explanations"),
            ("2", "Intermediate", "Familiar with basics, ready for deeper concepts"),
            ("3", "Advanced", "Strong understanding, can handle complex theory"),
        ]

        for choice, level, desc in levels:
            table.add_row(f"[{choice}]", level, desc)

        self.console.print(table)
        self.console.print()

        choice = Prompt.ask(
            "Your choice",
            choices=["1", "2", "3"],
            default="2"
        )

        mapping = {
            "1": LearningLevel.BEGINNER,
            "2": LearningLevel.INTERMEDIATE,
            "3": LearningLevel.ADVANCED,
        }

        level = mapping[choice]
        self.console.print(f"Selected: [green]{level.value}[/green]\n")
        return level

    def _ask_learning_goal(self) -> LearningGoal:
        """Ask user for their learning goal."""
        self.console.print("[bold cyan]Step 2/5: What's your primary learning goal?[/bold cyan]\n")

        # Create options table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Choice", style="yellow")
        table.add_column("Goal", style="cyan")
        table.add_column("Description")

        goals = [
            ("1", "Quick Review", "Brief refresher of concepts"),
            ("2", "Deep Learning", "Thorough understanding with practice"),
            ("3", "Exam Prep", "Focused preparation for tests"),
            ("4", "Research", "In-depth exploration for projects"),
        ]

        for choice, goal, desc in goals:
            table.add_row(f"[{choice}]", goal, desc)

        self.console.print(table)
        self.console.print()

        choice = Prompt.ask(
            "Your choice",
            choices=["1", "2", "3", "4"],
            default="2"
        )

        mapping = {
            "1": LearningGoal.QUICK_REVIEW,
            "2": LearningGoal.DEEP_LEARNING,
            "3": LearningGoal.EXAM_PREP,
            "4": LearningGoal.RESEARCH,
        }

        goal = mapping[choice]
        self.console.print(f"Selected: [green]{goal.value}[/green]\n")
        return goal

    def _ask_explanation_style(self) -> ExplanationStyle:
        """Ask user for their preferred explanation style."""
        self.console.print("[bold cyan]Step 3/5: How do you prefer explanations?[/bold cyan]\n")

        # Create options table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Choice", style="yellow")
        table.add_column("Style", style="cyan")
        table.add_column("Description")

        styles = [
            ("1", "Intuitive", "Simple analogies and everyday examples"),
            ("2", "Balanced", "Mix of intuition and technical details"),
            ("3", "Technical", "Rigorous mathematical explanations"),
        ]

        for choice, style, desc in styles:
            table.add_row(f"[{choice}]", style, desc)

        self.console.print(table)
        self.console.print()

        choice = Prompt.ask(
            "Your choice",
            choices=["1", "2", "3"],
            default="2"
        )

        mapping = {
            "1": ExplanationStyle.INTUITIVE,
            "2": ExplanationStyle.BALANCED,
            "3": ExplanationStyle.TECHNICAL,
        }

        style = mapping[choice]
        self.console.print(f"Selected: [green]{style.value}[/green]\n")
        return style

    def _ask_rag_preference(self) -> RAGFallbackPreference:
        """Ask user for RAG fallback preference."""
        self.console.print("[bold cyan]Step 4/5: Document-Based Learning[/bold cyan]\n")

        # Explain the feature
        explanation = Panel(
            """Academe can answer questions in two ways:

1. From YOUR documents (textbooks, notes, papers you upload)
2. From general AI knowledge (when your docs don't cover the topic)

When your documents don't have an answer, what should I do?""",
            title="How Academe Works",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(explanation)
        self.console.print()

        # Show options
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Choice", style="yellow")
        table.add_column("Option", style="cyan")
        table.add_column("Description")

        options = [
            ("1", "Ask me each time", "I'll offer choices: use general knowledge, upload docs, or rephrase"),
            ("2", "Use general knowledge", "I'll answer from AI knowledge when your docs don't help"),
            ("3", "Only use my documents", "I'll never use general knowledge (strict mode)"),
        ]

        for choice, option, desc in options:
            table.add_row(f"[{choice}]", option, desc)

        self.console.print(table)
        self.console.print()

        # Additional context for each option
        self.console.print("[dim]Recommended for new users: Option 1 (Ask each time)[/dim]")
        self.console.print("[dim]Great for mixing materials: Option 2 (Use general knowledge)[/dim]")
        self.console.print("[dim]Strict course study: Option 3 (Only documents)[/dim]\n")

        choice = Prompt.ask(
            "Your preference",
            choices=["1", "2", "3"],
            default="1"
        )

        mapping = {
            "1": RAGFallbackPreference.ALWAYS_ASK,
            "2": RAGFallbackPreference.PREFER_GENERAL,
            "3": RAGFallbackPreference.STRICT_DOCUMENTS,
        }

        preference = mapping[choice]
        self.console.print(f"Selected: [green]{preference.get_description()}[/green]\n")

        # Add helpful note based on choice
        if preference == RAGFallbackPreference.STRICT_DOCUMENTS:
            self.console.print("[dim]Tip: Upload your course materials first to get the best results.[/dim]\n")
        elif preference == RAGFallbackPreference.PREFER_GENERAL:
            self.console.print("[dim]Note: I'll always cite sources when using your documents.[/dim]\n")
        else:
            self.console.print("[dim]You can change this preference anytime in Settings.[/dim]\n")

        return preference

    def _ask_additional_preferences(self) -> Dict:
        """Ask for additional preferences."""
        self.console.print("[bold cyan]Step 5/5: Additional preferences[/bold cyan]\n")

        prefs = {}

        # Math formulas preference
        prefs["include_math_formulas"] = Confirm.ask(
            "Include mathematical formulas in explanations?",
            default=True
        )

        # Visualizations preference
        prefs["include_visualizations"] = Confirm.ask(
            "Include ASCII visualizations and diagrams?",
            default=True
        )

        # Code language preference
        languages = ["python", "javascript", "java", "cpp"]
        self.console.print("\nPreferred programming language for examples:")
        for i, lang in enumerate(languages, 1):
            self.console.print(f"  [{i}] {lang}")

        lang_choice = Prompt.ask(
            "Your choice",
            choices=[str(i) for i in range(1, len(languages) + 1)],
            default="1"
        )
        prefs["preferred_code_language"] = languages[int(lang_choice) - 1]

        self.console.print()
        return prefs

    def _confirm_preferences(self, preferences: Dict) -> bool:
        """
        Show preference summary and ask for confirmation.

        Args:
            preferences: Collected preferences

        Returns:
            True if user confirms, False to restart
        """
        self.console.print("[bold cyan]Your Preferences Summary:[/bold cyan]\n")

        # Create summary table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="yellow")

        # Format preferences for display
        display_map = {
            "learning_level": "Learning Level",
            "learning_goal": "Learning Goal",
            "explanation_style": "Explanation Style",
            "rag_fallback_preference": "Document Mode",
            "include_math_formulas": "Include Math",
            "include_visualizations": "Include Visuals",
            "preferred_code_language": "Code Language",
        }

        for key, label in display_map.items():
            if key in preferences:
                value = preferences[key]
                if isinstance(value, bool):
                    value = "Yes" if value else "No"
                elif hasattr(value, 'value'):
                    value = value.value.replace('_', ' ').title()
                elif hasattr(value, 'get_description'):
                    value = value.get_description()
                table.add_row(label, str(value))

        self.console.print(table)
        self.console.print()

        return Confirm.ask(
            "Save these preferences?",
            default=True
        )

    def save_preferences(self, user_id: str, preferences: Dict) -> bool:
        """
        Save user preferences to database.

        Args:
            user_id: User's ID
            preferences: Preferences to save

        Returns:
            True if saved successfully
        """
        try:
            # Add completion flag
            preferences["has_completed_onboarding"] = True

            # Convert enums to values for storage
            for key, value in list(preferences.items()):
                if hasattr(value, 'value'):
                    preferences[key] = value.value

            # Update user in database
            success = self.user_repo.update_user(user_id, preferences)

            if success:
                logger.info(f"Saved onboarding preferences for user {user_id}")
            else:
                logger.error(f"Failed to save preferences for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error saving preferences: {e}")
            return False

    def _show_completion_message(self) -> None:
        """Show onboarding completion message."""
        completion_panel = Panel(
            "[green]Onboarding Complete![/green]\n\n"
            "[white]Your preferences have been saved. Academe will now provide "
            "personalized explanations and code examples tailored to your "
            "learning style.\n\n"
            "You can update these preferences anytime using the [cyan]settings[/cyan] command.[/white]",
            title="[bold green]Welcome to Academe![/bold green]",
            border_style="green",
            padding=(1, 2),
        )
        self.console.print(completion_panel)
        self.console.print()

        # Wait for user to acknowledge
        Prompt.ask("Press [cyan]Enter[/cyan] to continue")

    def quick_setup(self, user: UserProfile) -> UserProfile:
        """
        Quick setup with default preferences for testing.

        Args:
            user: User profile

        Returns:
            Updated user profile
        """
        preferences = {
            "learning_level": LearningLevel.INTERMEDIATE.value,
            "learning_goal": LearningGoal.DEEP_LEARNING.value,
            "explanation_style": ExplanationStyle.BALANCED.value,
            "rag_fallback_preference": RAGFallbackPreference.ALWAYS_ASK.value,
            "include_math_formulas": True,
            "include_visualizations": True,
            "preferred_code_language": "python",
            "has_completed_onboarding": True,
            "has_seen_rag_explanation": True,
        }

        if self.save_preferences(user.id, preferences):
            # Convert back to enums for user object
            for key, value in preferences.items():
                if key == "learning_level":
                    value = LearningLevel(value)
                elif key == "learning_goal":
                    value = LearningGoal(value)
                elif key == "explanation_style":
                    value = ExplanationStyle(value)
                elif key == "rag_fallback_preference":
                    value = RAGFallbackPreference(value)
                setattr(user, key, value)

        return user