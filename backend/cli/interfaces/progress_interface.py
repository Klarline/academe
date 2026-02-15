from core.utils.datetime_utils import get_current_time
"""
Progress Dashboard Interface for Academe

Displays learning progress, study analytics, and recommendations.
Part of the enhanced Memory Module.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from core.utils.datetime_utils import get_current_time

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.columns import Columns
    from rich.prompt import Prompt
except ImportError:
    # Fallback for testing
    Console = None

from core.models import UserProfile
from core.database import ProgressRepository, get_database

logger = logging.getLogger(__name__)


class ProgressInterface:
    """Interface for learning progress and analytics."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize progress interface."""
        if Console:
            self.console = console or Console()
        else:
            self.console = None

        db = get_database()
        self.progress_repo = ProgressRepository(database=db)

    def show_dashboard(self, user: UserProfile) -> None:
        """
        Display the main learning dashboard.

        Args:
            user: User profile
        """
        if not self.console:
            print("📊 Learning Dashboard")
            print("(Rich library not available)")
            return

        # Get dashboard data
        dashboard = self._build_dashboard_data(user.id)

        # Display header
        self.console.print("\n[bold cyan]📊 Learning Progress Dashboard[/bold cyan]\n")

        # Display overview stats
        self._display_overview_stats(dashboard)

        # Display mastery distribution
        self._display_mastery_distribution(dashboard)

        # Display weak areas
        self._display_weak_areas(dashboard)

        # Display recommendations
        self._display_recommendations(dashboard)

        # Display study streak
        self._display_study_streak(dashboard)

    def show_detailed_progress(self, user: UserProfile) -> None:
        """
        Show detailed progress for all concepts.

        Args:
            user: User profile
        """
        if not self.console:
            print("📈 Detailed Progress")
            return

        progress_list = self.progress_repo.get_user_progress(user.id)

        if not progress_list:
            self.console.print("[yellow]No learning progress recorded yet.[/yellow]")
            return

        # Create table
        table = Table(
            title="Concept Progress Details",
            show_lines=True,
            header_style="bold cyan"
        )

        table.add_column("Concept", style="white")
        table.add_column("Mastery", justify="center")
        table.add_column("Score", justify="right", style="cyan")
        table.add_column("Attempts", justify="right")
        table.add_column("Accuracy", justify="right")
        table.add_column("Last Studied", style="dim")

        # Sort by mastery score
        progress_list.sort(key=lambda p: p.mastery_score, reverse=True)

        for progress in progress_list:
            # Color code mastery level
            mastery_color = {
                "expert": "green",
                "proficient": "bright_green",
                "competent": "yellow",
                "learning": "bright_yellow",
                "novice": "red"
            }.get(progress.mastery_level, "white")

            table.add_row(
                progress.concept.replace("_", " ").title(),
                f"[{mastery_color}]{progress.mastery_level}[/{mastery_color}]",
                f"{progress.mastery_score:.0%}",
                str(progress.questions_attempted),
                f"{progress.accuracy_rate:.0%}" if progress.questions_attempted > 0 else "-",
                progress.last_studied.strftime("%Y-%m-%d") if progress.last_studied else "-"
            )

        self.console.print(table)

    def show_study_sessions(self, user: UserProfile) -> None:
        """
        Display recent study sessions.

        Args:
            user: User profile
        """
        if not self.console:
            print("📚 Study Sessions")
            return

        sessions = self.progress_repo.get_study_sessions(user.id, days_back=14)

        if not sessions:
            self.console.print("[yellow]No study sessions recorded yet.[/yellow]")
            return

        # Create table
        table = Table(
            title="Recent Study Sessions (Last 14 Days)",
            show_lines=True,
            header_style="bold cyan"
        )

        table.add_column("Date", style="white")
        table.add_column("Duration", justify="right", style="cyan")
        table.add_column("Type", justify="center")
        table.add_column("Questions", justify="right")
        table.add_column("Accuracy", justify="right")
        table.add_column("Concepts", style="dim")

        for session in sessions:
            # Format duration
            duration = f"{session.duration_minutes:.0f} min"

            # Format accuracy
            accuracy = "-"
            if session.practice_problems_solved > 0:
                accuracy = f"{session.average_accuracy:.0%}"

            # Format concepts (first 3)
            concepts = ", ".join(session.concepts_studied[:3])
            if len(session.concepts_studied) > 3:
                concepts += f" (+{len(session.concepts_studied) - 3})"

            table.add_row(
                session.session_start.strftime("%Y-%m-%d %H:%M"),
                duration,
                session.session_type,
                str(session.questions_asked),
                accuracy,
                concepts or "-"
            )

        self.console.print(table)

    def _display_overview_stats(self, dashboard: Dict[str, Any]) -> None:
        """Display overview statistics."""
        stats_text = f"""
[bold]Overview[/bold]
• Total Concepts Studied: {dashboard.get('total_concepts_studied', 0)}
• Concepts Mastered: {dashboard.get('concepts_mastered', 0)}
• Study Streak: {dashboard.get('study_streak_days', 0)} days
• Total Study Time: {dashboard.get('total_study_time_hours', 0):.1f} hours
• Recent Sessions: {dashboard.get('recent_sessions', 0)} (last 7 days)
"""

        panel = Panel(
            stats_text.strip(),
            title="📊 Statistics",
            border_style="cyan"
        )
        self.console.print(panel)

    def _display_mastery_distribution(self, dashboard: Dict[str, Any]) -> None:
        """Display mastery level distribution."""
        mastery = dashboard.get('mastery_distribution', {})

        if not mastery:
            return

        # Create visual bars
        lines = ["[bold]Mastery Distribution[/bold]\n"]

        levels = [
            ("Expert", "expert", "green"),
            ("Proficient", "proficient", "bright_green"),
            ("Competent", "competent", "yellow"),
            ("Learning", "learning", "bright_yellow"),
            ("Novice", "novice", "red")
        ]

        max_count = max(mastery.values()) if mastery else 1

        for label, key, color in levels:
            count = mastery.get(key, 0)
            bar_width = int((count / max_count) * 20) if max_count > 0 else 0
            bar = "█" * bar_width
            lines.append(f"  [{color}]{label:10} {bar:20} {count}[/{color}]")

        panel = Panel(
            "\n".join(lines),
            title="📈 Progress Levels",
            border_style="cyan"
        )
        self.console.print(panel)

    def _display_weak_areas(self, dashboard: Dict[str, Any]) -> None:
        """Display weak areas that need attention."""
        weak_areas = dashboard.get('weak_areas', [])

        if not weak_areas:
            return

        lines = ["[bold]Areas Needing Attention[/bold]\n"]
        for i, area in enumerate(weak_areas[:5], 1):
            formatted_area = area.replace("_", " ").title()
            lines.append(f"  {i}. [red]{formatted_area}[/red]")

        panel = Panel(
            "\n".join(lines),
            title="⚠️ Weak Areas",
            border_style="yellow"
        )
        self.console.print(panel)

    def _display_recommendations(self, dashboard: Dict[str, Any]) -> None:
        """Display study recommendations."""
        recommendations = dashboard.get('recommendations', [])

        if not recommendations:
            return

        lines = ["[bold]Personalized Study Recommendations[/bold]\n"]

        for rec in recommendations[:5]:
            concept = rec['concept'].replace("_", " ").title()
            reason = rec['reason']
            mastery = rec.get('mastery_level', 'unknown')

            # Color code by mastery
            color = {
                "expert": "green",
                "proficient": "bright_green",
                "competent": "yellow",
                "learning": "bright_yellow",
                "novice": "red"
            }.get(mastery, "white")

            lines.append(f"  • [{color}]{concept}[/{color}]")
            lines.append(f"    [dim]{reason}[/dim]")

        panel = Panel(
            "\n".join(lines),
            title="💡 Recommendations",
            border_style="green"
        )
        self.console.print(panel)

    def _display_study_streak(self, dashboard: Dict[str, Any]) -> None:
        """Display study streak motivational message."""
        streak = dashboard.get('study_streak_days', 0)

        if streak == 0:
            message = "Start your streak today! 🚀"
            color = "yellow"
        elif streak < 7:
            message = f"Keep going! {streak} day{'s' if streak > 1 else ''} strong! 💪"
            color = "cyan"
        elif streak < 30:
            message = f"Amazing! {streak} days in a row! 🔥"
            color = "green"
        else:
            message = f"Incredible! {streak} day streak! You're on fire! 🏆"
            color = "bright_green"

        panel = Panel(
            f"[bold {color}]{message}[/bold {color}]",
            title="🔥 Study Streak",
            border_style=color
        )
        self.console.print(panel)

    def show_progress_menu(self) -> str:
        """
        Show progress menu options.

        Returns:
            Selected option
        """
        if not self.console:
            return "0"

        self.console.print("\n[bold cyan]Progress & Analytics[/bold cyan]\n")

        self.console.print("  [yellow]1[/yellow] - Dashboard Overview")
        self.console.print("  [yellow]2[/yellow] - Detailed Progress")
        self.console.print("  [yellow]3[/yellow] - Study Sessions")
        self.console.print("  [yellow]4[/yellow] - Export Progress")
        self.console.print("  [yellow]0[/yellow] - Back to Main Menu\n")

        if Prompt:
            choice = Prompt.ask(
                "Your choice",
                choices=["0", "1", "2", "3", "4"],
                default="1"
            )
        else:
            choice = input("Your choice: ")

        return choice

    def export_progress(self, user: UserProfile) -> bool:
        """
        Export progress data to JSON.

        Args:
            user: User profile

        Returns:
            Success status
        """
        try:
            import json
            from pathlib import Path

            # Get all progress data
            dashboard = self._build_dashboard_data(user.id)
            progress_list = self.progress_repo.get_user_progress(user.id)
            sessions = self.progress_repo.get_study_sessions(user.id, days_back=30)

            # Prepare export data
            export_data = {
                "user_id": user.id,
                "username": user.username,
                "export_date": get_current_time().isoformat(),
                "dashboard_summary": dashboard,
                "concept_progress": [
                    {
                        "concept": p.concept,
                        "mastery_level": p.mastery_level,
                        "mastery_score": p.mastery_score,
                        "questions_attempted": p.questions_attempted,
                        "accuracy_rate": p.accuracy_rate,
                        "last_studied": p.last_studied.isoformat() if p.last_studied else None
                    }
                    for p in progress_list
                ],
                "study_sessions": [
                    {
                        "date": s.session_start.isoformat(),
                        "duration_minutes": s.duration_minutes,
                        "questions_asked": s.questions_asked,
                        "accuracy": s.average_accuracy,
                        "concepts": s.concepts_studied
                    }
                    for s in sessions
                ]
            }

            # Save to file
            filename = f"academe_progress_{user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = Path(filename)

            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)

            if self.console:
                self.console.print(f"[green]✅ Progress exported to {filepath}[/green]")
            else:
                print(f"Progress exported to {filepath}")

            return True

        except Exception as e:
            logger.error(f"Error exporting progress: {e}")
            if self.console:
                self.console.print(f"[red]Error exporting progress: {e}[/red]")
            return False
    
    def _build_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """Build dashboard data from progress repository."""
        try:
            progress_list = self.progress_repo.get_user_progress(user_id)
            
            total_concepts = len(progress_list)
            concepts_mastered = len([
                p for p in progress_list 
                if p.mastery_level in ["proficient", "expert"]
            ])
            
            mastery_distribution = {}
            for p in progress_list:
                level = p.mastery_level
                mastery_distribution[level] = mastery_distribution.get(level, 0) + 1
            
            weak_areas = self.progress_repo.get_weak_areas(user_id, threshold=0.6)
            recommendations = self.progress_repo.get_study_recommendations(user_id, limit=5)
            sessions = self.progress_repo.get_study_sessions(user_id, days_back=30)
            
            study_streak_days = len(set(s.session_start.date() for s in sessions))
            total_study_time = sum(p.total_study_time_minutes for p in progress_list)
            
            return {
                "total_concepts_studied": total_concepts,
                "concepts_mastered": concepts_mastered,
                "mastery_distribution": mastery_distribution,
                "weak_areas": weak_areas,
                "recommendations": recommendations,
                "study_streak_days": study_streak_days,
                "total_study_time_hours": total_study_time / 60,
                "recent_sessions": len(sessions)
            }
        except Exception as e:
            logger.error(f"Error building dashboard: {e}")
            return {"total_concepts_studied": 0}


# Export interface
__all__ = ["ProgressInterface"]