"""Document management interface for Academe v0.3."""

import logging
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from academe.documents import DocumentManager
from academe.models import Document, DocumentStatus
from academe.rag import RAGPipeline

logger = logging.getLogger(__name__)


class DocumentInterface:
    """Interface for document management in CLI."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize document interface."""
        self.console = console or Console()
        self.doc_manager = DocumentManager()
        self.rag_pipeline = RAGPipeline()

    def show_document_menu(self, user_id: str) -> str:
        """
        Show document management menu.

        Args:
            user_id: User ID

        Returns:
            Selected option
        """
        self.console.print("\n[bold cyan]Document Management[/bold cyan]\n")

        # Get document stats
        stats = self.doc_manager.get_document_stats(user_id)

        # Show stats
        self.console.print(f"📚 Your Library: {stats['total_documents']} documents")
        self.console.print(f"   Ready: {stats['ready_documents']} | Processing: {stats.get('processing_documents', 0)}")
        self.console.print(f"   Total size: {stats['total_size_mb']:.1f} MB\n")

        # Menu options
        self.console.print("  [yellow]1[/yellow] - Upload Document")
        self.console.print("  [yellow]2[/yellow] - View Documents")
        self.console.print("  [yellow]3[/yellow] - Search Documents")
        self.console.print("  [yellow]4[/yellow] - Delete Document")
        self.console.print("  [yellow]0[/yellow] - Back to Main Menu\n")

        choice = Prompt.ask(
            "Your choice",
            choices=["0", "1", "2", "3", "4"],
            default="0"
        )

        return choice

    def upload_document(self, user_id: str) -> bool:
        """
        Handle document upload.

        Args:
            user_id: User ID

        Returns:
            True if upload successful
        """
        self.console.print("\n[bold cyan]Upload Document[/bold cyan]\n")

        # Get file path
        file_path = Prompt.ask("Enter file path (PDF, TXT, or MD)")

        # Check if file exists
        path = Path(file_path)
        if not path.exists():
            self.console.print(f"[red]File not found: {file_path}[/red]")
            return False

        # Get optional metadata
        title = Prompt.ask(
            "Document title",
            default=path.stem
        )

        tags_input = Prompt.ask(
            "Tags (comma-separated)",
            default=""
        )
        tags = [t.strip() for t in tags_input.split(",")] if tags_input else []

        course = Prompt.ask(
            "Course/Subject",
            default=""
        )

        # Upload with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Uploading and processing...", total=None)

            # Process document
            success, message, document = self.rag_pipeline.process_document_upload(
                file_path=str(path),
                user_id=user_id,
                title=title,
                tags=tags,
                course=course if course else None
            )

            progress.stop()

        if success:
            self.console.print(f"[green]✅ {message}[/green]")
            if document:
                self._show_document_details(document)
            return True
        else:
            self.console.print(f"[red]❌ {message}[/red]")
            return False

    def view_documents(self, user_id: str) -> Optional[str]:
        """
        Display user's documents.

        Args:
            user_id: User ID

        Returns:
            Selected document ID or None
        """
        documents = self.doc_manager.get_user_documents(user_id)

        if not documents:
            self.console.print("[yellow]No documents found.[/yellow]")
            return None

        # Create table
        table = Table(
            title="Your Documents",
            show_lines=True,
            header_style="bold cyan"
        )

        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="white")
        table.add_column("Type", justify="center", style="cyan")
        table.add_column("Pages", justify="right", style="yellow")
        table.add_column("Chunks", justify="right", style="green")
        table.add_column("Status", justify="center")
        table.add_column("Uploaded", style="dim")

        for idx, doc in enumerate(documents, 1):
            status_icon = {
                DocumentStatus.READY: "✅",
                DocumentStatus.PROCESSING: "⏳",
                DocumentStatus.FAILED: "❌",
                DocumentStatus.UPLOADED: "📤"
            }.get(doc.processing_status, "❓")

            table.add_row(
                str(idx),
                doc.title or doc.original_filename,
                doc.document_type.value.upper(),
                str(doc.page_count or "-"),
                str(doc.chunk_count),
                status_icon,
                doc.uploaded_at.strftime("%Y-%m-%d")
            )

        self.console.print(table)

        # Allow selection
        self.console.print("\nEnter document # to view details (0 to cancel)")
        choice = Prompt.ask(
            "Select document",
            default="0"
        )

        if choice == "0" or not choice.isdigit():
            return None

        idx = int(choice) - 1
        if 0 <= idx < len(documents):
            doc = documents[idx]
            self._show_document_details(doc)
            return doc.id

        return None

    def search_documents(self, user_id: str) -> None:
        """
        Search user's documents.

        Args:
            user_id: User ID
        """
        query = Prompt.ask("Search query")

        results = self.doc_manager.search_documents(
            user_id=user_id,
            query=query,
            limit=10
        )

        if not results:
            self.console.print("[yellow]No matching documents found.[/yellow]")
            return

        self.console.print(f"\n[green]Found {len(results)} matching documents:[/green]\n")

        for doc in results:
            self.console.print(f"• {doc.title or doc.original_filename}")
            if doc.tags:
                self.console.print(f"  Tags: {', '.join(doc.tags)}", style="dim")

    def delete_document(self, user_id: str) -> bool:
        """
        Delete a document.

        Args:
            user_id: User ID

        Returns:
            True if deleted
        """
        # Show documents
        documents = self.doc_manager.get_user_documents(user_id)

        if not documents:
            self.console.print("[yellow]No documents to delete.[/yellow]")
            return False

        # Display list
        self.console.print("\n[bold red]Delete Document[/bold red]\n")

        for idx, doc in enumerate(documents, 1):
            self.console.print(
                f"  [{idx}] {doc.title or doc.original_filename} "
                f"({doc.chunk_count} chunks)"
            )

        # Get selection
        choice = Prompt.ask(
            "Select document to delete (0 to cancel)",
            default="0"
        )

        if choice == "0" or not choice.isdigit():
            return False

        idx = int(choice) - 1
        if 0 <= idx < len(documents):
            doc = documents[idx]

            # Confirm deletion
            if Confirm.ask(
                f"Delete '{doc.title or doc.original_filename}'?",
                default=False
            ):
                success, message = self.doc_manager.delete_document(
                    document_id=doc.id,
                    user_id=user_id,
                    delete_file=True
                )

                if success:
                    self.console.print(f"[green]✅ {message}[/green]")
                else:
                    self.console.print(f"[red]❌ {message}[/red]")

                return success

        return False

    def _show_document_details(self, document: Document) -> None:
        """Display detailed document information."""
        details = Panel(
            f"""[bold]{document.title or document.original_filename}[/bold]

[cyan]Type:[/cyan] {document.document_type.value}
[cyan]Status:[/cyan] {document.processing_status.value}
[cyan]File:[/cyan] {document.original_filename}
[cyan]Size:[/cyan] {document.file_size / 1024:.1f} KB
[cyan]Pages:[/cyan] {document.page_count or 'N/A'}
[cyan]Chunks:[/cyan] {document.chunk_count}
[cyan]Course:[/cyan] {document.course or 'None'}
[cyan]Tags:[/cyan] {', '.join(document.tags) if document.tags else 'None'}
[cyan]Uploaded:[/cyan] {document.uploaded_at.strftime('%Y-%m-%d %H:%M')}""",
            title="Document Details",
            border_style="cyan"
        )

        self.console.print(details)