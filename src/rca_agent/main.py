"""Standalone Typer CLI entrypoint for rca-agent.

Provides command-line interfaces for:
- Autonomous root cause analysis on specific commits (investigate)
- Incident log, stack trace, and LGTM triage to discover culprit commits (triage)
- Release window multi-commit bisection (investigate --between)
- Automated guardrail test generation and Slack/GitHub incident reporting
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table as RichTable
from rich.text import Text

from rca_agent.agent.factory import resolve_provider_and_key
from rca_agent.agent.investigator import run_investigation
from rca_agent.core.forensics import set_repo_path
from rca_agent.core.lgtm import extract_traceback_from_lgtm
from rca_agent.core.range_analyzer import parse_commit_range
from rca_agent.core.triage import find_culprit_from_log
from rca_agent.models.schema import BlamelessRCA
from rca_agent.reports.guardrails import write_regression_test_file
from rca_agent.reports.notifier import format_github_pr_markdown, send_slack_notification
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
    """Render a structured BlamelessRCA report cleanly to the terminal."""
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


def dispatch_reports(
    rca: BlamelessRCA,
    commit_hash: str,
    repo_name: str,
    model_name: str,
    pdf: str | None = None,
    generate_test: str | None = None,
    slack_webhook: str | None = None,
    markdown_pr: str | None = None,
) -> None:
    """Handle all secondary report generation, test output, and notifications."""
    if pdf:
        pdf_file = Path(pdf).expanduser().resolve()
        try:
            generate_rca_pdf(
                rca=rca,
                output_path=pdf_file,
                commit_hash=commit_hash,
                repo_name=repo_name,
                model_name=model_name,
            )
            console.print(
                f"[bold green]✓ Executive PDF report generated:[/bold green] [cyan]{pdf_file}[/cyan]"
            )
        except Exception as exc:
            console.print(f"[bold red]PDF Generation Warning:[/bold red] Failed to generate PDF: {exc}")

    if generate_test:
        test_dir = Path(generate_test).expanduser().resolve()
        try:
            created_test = write_regression_test_file(
                rca=rca,
                commit_hash=commit_hash,
                output_dir=test_dir,
            )
            console.print(
                f"[bold green]✓ Regression test guardrail created:[/bold green] [cyan]{created_test}[/cyan]"
            )
        except Exception as exc:
            console.print(f"[bold red]Test Generation Warning:[/bold red] Failed to create test: {exc}")

    if markdown_pr:
        pr_path = Path(markdown_pr).expanduser().resolve()
        try:
            pr_content = format_github_pr_markdown(rca=rca, commit_hash=commit_hash, repo_name=repo_name)
            pr_path.parent.mkdir(parents=True, exist_ok=True)
            pr_path.write_text(pr_content, encoding="utf-8")
            console.print(
                f"[bold green]✓ GitHub PR comment markdown exported:[/bold green] [cyan]{pr_path}[/cyan]"
            )
        except Exception as exc:
            console.print(f"[bold red]Markdown Export Warning:[/bold red] Failed to export PR comment: {exc}")

    if slack_webhook:
        try:
            success = send_slack_notification(
                webhook_url=slack_webhook,
                rca=rca,
                commit_hash=commit_hash,
                repo_name=repo_name,
            )
            if success:
                console.print("[bold green]✓ Slack incident briefing dispatched successfully.[/bold green]")
            else:
                console.print("[bold yellow]Slack Warning:[/bold yellow] Webhook rejected the request.")
        except Exception as exc:
            console.print(f"[bold red]Slack Notification Error:[/bold red] {exc}")


@app.command()
def investigate(
    commit: str | None = typer.Option(
        None,
        "--commit",
        "-c",
        help="The Git commit hash (SHA) to investigate.",
    ),
    between: str | None = typer.Option(
        None,
        "--between",
        "-b",
        help="Commit revision range to analyze (e.g. v1.0.0..HEAD or SHA1..SHA2).",
    ),
    symptom: str | None = typer.Option(
        None,
        "--symptom",
        "-s",
        help="Observed error symptom or subsystem keyword to isolate culprit in --between range.",
    ),
    path: str = typer.Option(
        ".",
        "--path",
        "-p",
        help="Path to the target Git repository root.",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        "-P",
        help="LLM provider: gemini, openrouter, openai, ollama (auto-detected if omitted).",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Model ID (e.g. gemini-3.6-flash, anthropic/claude-3.5-sonnet, gpt-4o).",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for the selected provider (overrides environment variables).",
    ),
    pdf: str | None = typer.Option(
        None,
        "--pdf",
        help="Optional file path to output an executive PDF postmortem report.",
    ),
    generate_test: str | None = typer.Option(
        None,
        "--generate-test",
        help="Optional directory to write an automated reproduction pytest test.",
    ),
    slack_webhook: str | None = typer.Option(
        None,
        "--slack-webhook",
        help="Optional Slack Incoming Webhook URL to broadcast incident briefing.",
    ),
    markdown_pr: str | None = typer.Option(
        None,
        "--markdown-pr",
        help="Optional path to output GitHub PR review comment markdown.",
    ),
) -> None:
    """Execute an autonomous Root Cause Analysis on a commit or revision range."""
    repo_path = Path(path).expanduser().resolve()
    if not repo_path.exists():
        console.print(
            f"[bold red]Error:[/bold red] Repository path '{repo_path}' does not exist.",
            style="red",
        )
        raise typer.Exit(code=1)

    target_commit = commit

    # Handle --between range analysis
    if between:
        console.print(f"[bold blue]Scanning release window:[/bold blue] [cyan]{between}[/cyan]")
        if symptom:
            console.print(f"[dim]Filtering by symptom:[/dim] {symptom}")

        range_matches = parse_commit_range(
            repo_path=str(repo_path),
            commit_range=between,
            symptom=symptom,
        )

        if not range_matches:
            console.print(f"[bold red]Error:[/bold red] No commits found in range '{between}'.")
            raise typer.Exit(code=1)

        # Render top candidate matches
        table = RichTable(title="🔍 Suspect Commits in Release Window", show_header=True)
        table.add_column("Score", style="bold green", width=8)
        table.add_column("Commit", style="cyan", width=10)
        table.add_column("Author", style="magenta")
        table.add_column("Summary")

        for match in range_matches[:5]:
            table.add_row(
                f"{int(match.score * 100)}%",
                match.commit_sha[:8],
                match.author,
                match.summary,
            )
        console.print(table)
        console.print()

        target_commit = range_matches[0].commit_sha
        console.print(
            f"[bold green]Selected primary suspect for deep RCA:[/bold green] [cyan]{target_commit}[/cyan]\n"
        )

    if not target_commit:
        console.print(
            "[bold red]Error:[/bold red] You must specify either --commit <SHA> or --between <range>.",
            style="red",
        )
        raise typer.Exit(code=1)

    resolved_provider, resolved_model, resolved_key = resolve_provider_and_key(
        provider=provider, model=model, api_key=api_key
    )

    if resolved_provider != "ollama" and not resolved_key:
        console.print(
            f"[bold yellow]Notice:[/bold yellow] No API key detected for provider '[bold cyan]{resolved_provider}[/bold cyan]'.\n"
            "Configure one of the following environment variables (or pass --api-key):\n"
            "  • OpenRouter:  OPENROUTER_API_KEY\n"
            "  • Gemini:      GEMINI_API_KEY (or GOOGLE_API_KEY)\n"
            "  • OpenAI:      OPENAI_API_KEY\n"
        )

    console.print(
        f"[bold blue]Initiating RCA investigation for commit:[/bold blue] [cyan]{target_commit}[/cyan]"
    )
    console.print(f"[dim]Repository:[/dim] {repo_path}")
    console.print(f"[dim]Provider:[/dim]   {resolved_provider}")
    console.print(f"[dim]Model:[/dim]      {resolved_model}\n")

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
            rca_result = run_investigation(
                commit_hash=target_commit,
                model_id=resolved_model,
                api_key=resolved_key,
                provider=resolved_provider,
            )
        except Exception as exc:
            console.print(f"\n[bold red]Investigation Failed:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc

    render_postmortem(rca_result)

    dispatch_reports(
        rca=rca_result,
        commit_hash=target_commit,
        repo_name=repo_path.name,
        model_name=f"{resolved_provider.title()}: {resolved_model}",
        pdf=pdf,
        generate_test=generate_test,
        slack_webhook=slack_webhook,
        markdown_pr=markdown_pr,
    )


@app.command()
def triage(
    log: Path | None = typer.Option(
        None,
        "--log",
        "-l",
        help="Path to crash log, traceback, or incident error file.",
    ),
    error: str | None = typer.Option(
        None,
        "--error",
        "-e",
        help="Direct exception message or traceback text string.",
    ),
    lgtm: Path | None = typer.Option(
        None,
        "--lgtm",
        help="Path to Grafana Loki JSON query export or Grafana Alert webhook JSON.",
    ),
    path: str = typer.Option(
        ".",
        "--path",
        "-p",
        help="Path to the target Git repository root.",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        "-P",
        help="LLM provider: gemini, openrouter, openai, ollama (auto-detected if omitted).",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Model ID (e.g. gemini-3.6-flash, anthropic/claude-3.5-sonnet, gpt-4o).",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for the selected provider (overrides environment variables).",
    ),
    pdf: str | None = typer.Option(
        None,
        "--pdf",
        help="Optional file path to output an executive PDF postmortem report.",
    ),
    generate_test: str | None = typer.Option(
        None,
        "--generate-test",
        help="Optional directory to write an automated reproduction pytest test.",
    ),
    slack_webhook: str | None = typer.Option(
        None,
        "--slack-webhook",
        help="Optional Slack Incoming Webhook URL to broadcast incident briefing.",
    ),
    markdown_pr: str | None = typer.Option(
        None,
        "--markdown-pr",
        help="Optional path to output GitHub PR review comment markdown.",
    ),
) -> None:
    """Triage a stack trace or log file to automatically discover and investigate the culprit commit."""
    repo_path = Path(path).expanduser().resolve()
    if not repo_path.exists():
        console.print(
            f"[bold red]Error:[/bold red] Repository path '{repo_path}' does not exist.",
            style="red",
        )
        raise typer.Exit(code=1)

    raw_text: str = ""

    # Source 1: LGTM / Loki JSON or Grafana Alert file
    if lgtm:
        lgtm_file = Path(lgtm).expanduser().resolve()
        if not lgtm_file.exists():
            console.print(f"[bold red]Error:[/bold red] LGTM log file '{lgtm_file}' not found.")
            raise typer.Exit(code=1)
        raw_text = extract_traceback_from_lgtm(lgtm_file.read_text(encoding="utf-8"))

    # Source 2: Standard log file
    elif log:
        log_file = Path(log).expanduser().resolve()
        if not log_file.exists():
            console.print(f"[bold red]Error:[/bold red] Log file '{log_file}' not found.")
            raise typer.Exit(code=1)
        raw_text = log_file.read_text(encoding="utf-8")

    # Source 3: Inline error text
    elif error:
        raw_text = error

    # Source 4: Piped stdin
    elif not sys.stdin.isatty():
        raw_text = sys.stdin.read()

    if not raw_text.strip():
        console.print(
            "[bold red]Error:[/bold red] No incident log or traceback provided.\n"
            "Pass --log <file>, --error <text>, --lgtm <file>, or pipe via stdin (`cat crash.log | rca-agent triage`).",
            style="red",
        )
        raise typer.Exit(code=1)

    console.print("[bold blue]Initiating Autonomous Log & Stack Trace Triage...[/bold blue]\n")

    best_sha, candidates = find_culprit_from_log(log_text=raw_text, repo_path=str(repo_path))

    if not best_sha:
        console.print(
            "[bold yellow]Triage Notice:[/bold yellow] No commit directly matched lines in the traceback.\n"
            "Ensure the stack trace contains file paths within this repository.",
            style="yellow",
        )
        raise typer.Exit(code=1)

    # Display ranked culprit candidates
    table = RichTable(title="🎯 Forensics Match Candidates", show_header=True)
    table.add_column("Confidence", style="bold green", width=12)
    table.add_column("Culprit Commit", style="cyan", width=14)
    table.add_column("File Location", style="magenta")
    table.add_column("Author")
    table.add_column("Commit Summary")

    for cand in candidates[:5]:
        table.add_row(
            f"{int(cand.confidence_score * 100)}%",
            cand.commit_sha[:8],
            f"{cand.file_path}:{cand.line_number}",
            cand.author,
            cand.summary,
        )
    console.print(table)
    console.print()

    console.print(
        f"[bold green]Isolated primary architectural fault culprit:[/bold green] [cyan]{best_sha}[/cyan]\n"
    )

    # Proceed to full RCA investigation
    resolved_provider, resolved_model, resolved_key = resolve_provider_and_key(
        provider=provider, model=model, api_key=api_key
    )

    set_repo_path(str(repo_path))

    with console.status(
        "[bold green]Generating Blameless Root Cause Analysis on culprit commit...", spinner="dots"
    ):
        try:
            rca_result = run_investigation(
                commit_hash=best_sha,
                model_id=resolved_model,
                api_key=resolved_key,
                provider=resolved_provider,
            )
        except Exception as exc:
            console.print(f"\n[bold red]Investigation Failed:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc

    render_postmortem(rca_result)

    dispatch_reports(
        rca=rca_result,
        commit_hash=best_sha,
        repo_name=repo_path.name,
        model_name=f"{resolved_provider.title()}: {resolved_model}",
        pdf=pdf,
        generate_test=generate_test,
        slack_webhook=slack_webhook,
        markdown_pr=markdown_pr,
    )


if __name__ == "__main__":
    app()
