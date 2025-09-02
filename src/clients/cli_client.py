"""CLI Client for MCP workflow interaction
Provides enhanced command-line interface to MCP agents with interactive features.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.markdown import Markdown
from rich import print as rprint

from src.utils.logger import get_logger
from src.utils.config import load_settings
from src.orchestrator.router import MCPRouter
from src.orchestrator.memory import MemoryManager
from src.orchestrator.conversational_agent import ConversationalAgent


class MCPCLIClient:
    """Enhanced CLI client for MCP workflow interaction"""
    
    def __init__(self):
        self.console = Console()
        self.logger = get_logger("mcp_cli")
        self.settings = load_settings()
        self.router = MCPRouter()
        self.memory = MemoryManager(self.settings)
        self.session_id: Optional[str] = None
        # Conversational layer for intent parsing and persona responses
        self.conv_agent = ConversationalAgent(self.settings)
    
    def _ensure_session(self):
        if not self.session_id:
            self.session_id = self.memory.create_session()
            self.console.print(f"[cyan]New session:[/cyan] {self.session_id}")

    def run_interactive(self):
        """Run interactive CLI session"""
        self.console.print(Panel.fit(
            "[bold blue]RouteWise AI - MCP Interactive CLI[/bold blue]\n"
            "Enhanced travel planning with multi-agent coordination\n\n"
            "Commands: plan, refine, add, budget, duration, show, why, list, new, resume, help, exit",
            border_style="blue"
        ))
        
        while True:
            try:
                cmd = Prompt.ask("\n[bold green]routewise>[/bold green]", default="help").strip()
                if not cmd:
                    continue
                if cmd.lower() in ("exit", "quit", "q"):
                    break
                
                parts = cmd.split(maxsplit=1)
                action = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                
                if action == "help":
                    self.show_help()
                elif action == "list":
                    self._list_sessions()
                elif action == "new":
                    self.session_id = self.memory.create_session()
                    self.console.print(f"[cyan]New session:[/cyan] {self.session_id}")
                elif action == "resume":
                    if not arg:
                        self.console.print("[yellow]Usage: resume <session_id>[/yellow]")
                    else:
                        self.session_id = arg
                        self.console.print(f"[cyan]Resumed session:[/cyan] {self.session_id}")
                elif action == "plan":
                    if not arg:
                        arg = Prompt.ask("Enter trip query", default="Delhi to Jaipur, 2 days, budget")
                    save = Confirm.ask("Save outputs?", default=True)
                    self._ensure_session()
                    self._process_query(arg, save, message_type="text")
                elif action == "refine":
                    if not arg:
                        arg = Prompt.ask("Enter refinement", default="reduce budget to ₹8000")
                    self._ensure_session()
                    self._process_query(arg, save=True, message_type="refinement")
                elif action == "add":
                    if not arg:
                        arg = Prompt.ask("Add preference/location", default="include scuba diving")
                    self._ensure_session()
                    self._process_query(f"Add: {arg}", save=True, message_type="refinement")
                elif action == "budget":
                    if not arg:
                        arg = Prompt.ask("Set budget range", default="under ₹8000 total")
                    self._ensure_session()
                    self._process_query(f"Adjust budget: {arg}", save=True, message_type="refinement")
                elif action == "duration":
                    if not arg:
                        arg = Prompt.ask("Set duration", default="extend to 4 days")
                    self._ensure_session()
                    self._process_query(f"Change duration: {arg}", save=True, message_type="refinement")
                elif action == "show":
                    self._show_current()
                elif action == "why":
                    if not arg:
                        arg = Prompt.ask("Ask why", default="why choose this hotel?")
                    self._ensure_session()
                    self._process_query(f"Why: {arg}", save=False, message_type="refinement")
                else:
                    self.console.print("[yellow]Unknown command. Type 'help' for commands.[/yellow]")
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Session interrupted by user[/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                self.logger.error(f"CLI error: {e}")

    def _list_sessions(self):
        sessions = self.memory.list_sessions(limit=10)
        if not sessions:
            self.console.print("[yellow]No sessions found[/yellow]")
            return
        
        self.console.print("\n[bold]Recent sessions:[/bold]")
        for s in sessions:
            self.console.print(f"- [cyan]{s['session_id']}[/cyan] | {s['trip_info']} | msgs: {s['message_count']} | updated: {s['last_updated']}")

    def _show_current(self):
        if not self.session_id:
            self.console.print("[yellow]No active session. Use 'plan' to start or 'resume <id>'.[/yellow]")
            return
        ctx = self.memory.get_trip_context(self.session_id)
        if not ctx or not ctx.current_itinerary:
            self.console.print("[yellow]No itinerary yet. Use 'plan' to create one.[/yellow]")
            return
        self.console.print("\n" + "="*60)
        self.console.print("[bold blue]Current Itinerary[/bold blue]")
        self.console.print("="*60)
        self.console.print(Markdown(ctx.current_itinerary))

    def run_single_query(self, query: str, save: bool = True) -> str:
        """Run single query and return result"""
        return self._process_query(query, save)
    
    def _process_query(self, query: str, save: bool, message_type: str = "text") -> str:
        """Process a single query through MCP workflow"""
        with self.console.status("[bold green]Processing query through MCP agents..."):
            try:
                if self.session_id is None:
                    # For one-shot mode, create ephemeral session to enable context-aware prompting
                    self.session_id = self.memory.create_session(initial_query=query)
                
                # Parse intent and enhance query with conversation context/persona
                intent = self.conv_agent.parse_intent(query, self.memory, self.session_id)
                enhanced_query = self.conv_agent.enhance_query_with_context(intent, self.memory, self.session_id)
                
                # Derive message type if not explicitly set
                derived_type = "refinement" if intent.intent_type in ("refine", "swap", "explain") else "text"
                msg_type = message_type or derived_type
                
                result = self.router.route(
                    enhanced_query, 
                    save=save, 
                    session_id=self.session_id, 
                    memory_manager=self.memory, 
                    message_type=msg_type
                )  # type: ignore[arg-type]
                
                # Add persona formatting and optional explanations
                formatted = self.conv_agent.format_response_with_persona(intent, result, self.memory, self.session_id)
                
                # Display results
                self.console.print("\n" + "="*60)
                self.console.print("[bold blue]Generated Itinerary[/bold blue]")
                self.console.print("="*60)
                
                # Render markdown for better display
                md = Markdown(formatted)
                self.console.print(md)
                
                if save:
                    self.console.print(f"\n[green]✓ Outputs saved to data/ directory[/green]")
                
                return formatted
                
            except Exception as e:
                error_msg = f"Failed to process query: {e}"
                self.console.print(f"\n[red]Error: {error_msg}[/red]")
                self.logger.error(error_msg)
                raise

    def show_help(self):
        """Display help information"""
        help_text = """
[bold blue]RouteWise AI - MCP CLI Client[/bold blue]

[bold]Usage:[/bold]
  Interactive mode: python -m src.clients.cli_client
  Single query:     python -m src.main "query" [--no-save]

[bold]Commands:[/bold]
  plan <query>         Start a new plan or update existing plan
  refine <text>        Ask to adjust current plan (budget, preferences, etc.)
  add <item>           Add preference or location
  budget <range>       Change budget constraints (e.g., under ₹8000)
  duration <text>      Change duration (e.g., extend to 4 days)
  show                 Show current itinerary
  why <question>       Ask why a choice was made and get explanation
  list                 List recent sessions
  new                  Start a new session
  resume <session_id>  Resume an existing session
  help                 Show this help
  exit                 Quit

[bold]Examples:[/bold]
  plan "Mumbai to Goa, 3 days, beach"
  refine "reduce budget to ₹8,000"
  add "include scuba diving"
  show
        """
        self.console.print(Panel(help_text, border_style="blue"))


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="RouteWise AI - Enhanced MCP CLI Client",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "query", 
        nargs="?", 
        help="Travel query (if not provided, enters interactive mode)"
    )
    parser.add_argument(
        "--no-save", 
        action="store_true", 
        help="Do not save outputs to files"
    )
    parser.add_argument(
        "--help-extended", 
        action="store_true", 
        help="Show extended help with examples"
    )
    
    return parser.parse_args()


def main():
    """Main CLI entry point"""
    args = parse_args()
    client = MCPCLIClient()
    
    if args.help_extended:
        client.show_help()
        return
    
    if args.query:
        # Single query mode
        try:
            client.run_single_query(args.query, save=(not args.no_save))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Interactive mode
        client.run_interactive()


if __name__ == "__main__":
    main()