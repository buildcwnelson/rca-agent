"""Standalone Typer CLI entrypoint for rca-agent.

Provides the command-line interface for running autonomous blameless
Root Cause Analysis investigations on Git repositories and rendering
rich, beautifully styled terminal postmortems.
"""

from __future__ import annotations

import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from rca_agent.agent.investigator import run_investigation
from rca_agent.core.forensics import set_repo_path
from rca_agent.models.schema import BlamelessRCA
from rca_agent.reports.pdf import generate_rca_pdf

# Automatically load environment variables from .env
load_dotenv()

app = typer.Typer(
    name="rca-agent",
    help="Autonomous Root Cause Analysis generator powered by Agno.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main_callback() -> None:
    """Autonomous Root Cause Analysis generator powered by Agno."""


def render_postmortem(rca: BlamelessRCA, custom_console: Console | None = None) -> None:
    """Render a structured BlamelessRCA report cleanly to the terminal.

    Utilizes Rich Panels, Markdown, and distinct color-coding for
    blast radius warnings (red/amber) and preventative action items (green/cyan).
    """
    out = custom_console or console

    # Header Banner
    header_text = Text(
        "🔍 BLAMELESS ROOT CAUSE ANALYSIS POSTMORTEM", style="bold white on blue", justify="center"
    )
    out.print()
    out.print(Panel(header_text, border_style="blue", padding=(1, 2)))

    # Executive Summary
    summary_md = Markdown(rca.executive_summary)
    out.print(
        Panel(
            summary_md,
            title="📋 [bold cyan]Executive Summary[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # Incident Timeline
    timeline_lines = []
    for i, event in enumerate(rca.incident_timeline, 1):
        timeline_lines.append(f"[bold cyan]T+{i:02d}[/bold cyan] │ {event}")
    timeline_text = Text.from_markup("\n".join(timeline_lines))
    out.print(
        Panel(
            timeline_text,
            title="⏱️ [bold blue]Incident Timeline (Structural Decay)[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        )
    )

    # Root Cause Analysis (5 Whys)
    rca_md = Markdown(rca.root_cause_analysis)
    out.print(
        Panel(
            rca_md,
            title="🎯 [bold magenta]Root Cause Analysis (5 Whys Framework)[/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        )
    )

    # Blast Radius (Warning Alert - Red / Amber)
    blast_lines = []
    for item in rca.blast_radius:
        blast_lines.append(f"[bold red]⚠️ IMPACT:[/bold red] [red]{item}[/red]")
    blast_text = Text.from_markup(
        "\n".join(blast_lines) if blast_lines else "[dim]No downstream blast radius detected.[/dim]"
    )
    out.print(
        Panel(
            blast_text,
            title="💥 [bold red]Blast Radius & Downstream Impact[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
    )

    # Preventative Action Items (Guardrails - Green / Emerald)
    actions_lines = []
    for i, action in enumerate(rca.preventative_action_items, 1):
        actions_lines.append(f"[bold green]🛡️ [{i}][/bold green] [green]{action}[/green]")
    actions_text = Text.from_markup(
        "\n".join(actions_lines) if actions_lines else "[dim]No preventative actions defined.[/dim]"
    )
    out.print(
        Panel(
            actions_text,
            title="🛡️ [bold green]Preventative Guardrails & Action Items[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )
    out.print(Rule(style="dim blue"))
    out.print()


@app.command()
def investigate(
    commit: str = typer.Option(
        ...,
        "--commit",
        "-c",
        help="The Git commit hash (SHA) to investigate for root cause analysis.",
    ),
    path: str = typer.Option(
        ".",
        "--path",
        "-p",
        help="Path to the target Git repository root.",
    ),
    model: str = typer.Option(
        "gemini-2.5-flash",
        "--model",
        "-m",
        help="Google Gemini model identifier from Google AI Studio (e.g. gemini-2.5-flash, gemini-2.5-pro).",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Google AI Studio API key (overrides GEMINI_API_KEY environment variable).",
    ),
    pdf: str | None = typer.Option(
        None,
        "--pdf",
        help="Optional file path to output an executive PDF postmortem report.",
    ),
) -> None:
    """Execute an autonomous Root Cause Analysis on a given commit."""
    repo_path = Path(path).expanduser().resolve()
    if not repo_path.exists():
        console.print(
            f"[bold red]Error:[/bold red] Repository path '{repo_path}' does not exist.",
            style="red",
        )
        raise typer.Exit(code=1)

    resolved_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not resolved_key:
        console.print(
            "[bold yellow]Notice:[/bold yellow] No GEMINI_API_KEY or GOOGLE_API_KEY detected in your environment or .env file.\n"
            "Please ensure you have configured your Google AI Studio API key in .env or pass --api-key.\n"
        )

    console.print(
        f"[bold blue]Initiating RCA investigation for commit:[/bold blue] [cyan]{commit}[/cyan]"
    )
    console.print(f"[dim]Repository:[/dim] {repo_path}")
    console.print(f"[dim]Reasoning Model:[/dim] {model}\n")

    try:
        set_repo_path(str(repo_path))
    except Exception as exc:
        console.print(
            f"[bold red]Forensics Error:[/bold red] Failed to initialize repository: {exc}"
        )
        raise typer.Exit(code=1) from exc

    with console.status(
        "[bold green]Executing Git forensics and 5 Whys analysis...", spinner="dots"
    ):
        try:
            rca_result = run_investigation(commit_hash=commit, model_id=model, api_key=resolved_key)
        except Exception as exc:
            console.print(f"\n[bold red]Investigation Failed:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc

    render_postmortem(rca_result)

    if pdf:
        pdf_file = Path(pdf).expanduser().resolve()
        try:
            generate_rca_pdf(
                rca=rca_result,
                output_path=pdf_file,
                commit_hash=commit,
                repo_name=repo_path.name,
                model_name=model,
            )
            console.print(
                f"[bold green]✓ Executive PDF report generated:[/bold green] [cyan]{pdf_file}[/cyan]\n"
            )
        except (OSError, RuntimeError, ValueError) as exc:
            console.print(
                f"[bold red]PDF Generation Warning:[/bold red] Failed to generate PDF: {exc}"
            )


if __name__ == "__main__":
    app()
