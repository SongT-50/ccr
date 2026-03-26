"""CCR command-line interface."""

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ccr.models import Severity
from ccr.reviewer import CCRReviewer

console = Console()

SEVERITY_COLORS = {
    Severity.CRITICAL: "red bold",
    Severity.MAJOR: "yellow",
    Severity.MINOR: "cyan",
    Severity.INFO: "dim",
}

SEVERITY_EMOJI = {
    Severity.CRITICAL: "!!",
    Severity.MAJOR: "! ",
    Severity.MINOR: "- ",
    Severity.INFO: "  ",
}


@click.group()
@click.version_option()
def main():
    """CCR: Cross-Context Review - LLM bias elimination through session isolation.

    Based on: Song (2026) "Cross-Context Review" arXiv:2603.12123
    """
    pass


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--provider", "-p", default="anthropic", help="LLM provider (anthropic/openai)")
@click.option("--model", "-m", default=None, help="Model name override")
@click.option("--reviewers", "-n", default=3, help="Number of independent reviewers (default: 3)")
@click.option("--type", "artifact_type", default=None, help="Artifact type (code/document/paper)")
@click.option("--output", "-o", default=None, help="Save report to file")
@click.option("--sequential", is_flag=True, help="Run reviewers sequentially (default: parallel)")
def review(file, provider, model, reviewers, artifact_type, output, sequential):
    """Review a file using Cross-Context Review protocol.

    Each reviewer runs in a completely isolated session - no shared context,
    no anchoring bias. Findings are merged by a Director session.

    Examples:

        ccr review mycode.py

        ccr review paper.tex --type paper --reviewers 5

        ccr review app.js --provider openai --model gpt-4o
    """
    console.print(f"\n[bold]CCR Review[/bold]: {file}")
    console.print(f"Provider: {provider} | Reviewers: {reviewers} | Parallel: {not sequential}\n")

    with console.status("[bold green]Running independent reviews..."):
        reviewer = CCRReviewer(
            provider=provider,
            model=model,
            num_reviewers=reviewers,
            parallel=not sequential,
        )
        result = reviewer.review_file(file, artifact_type=artifact_type)

    # Display results
    _display_results(result)

    # Save to file if requested
    if output:
        report = _format_report(result)
        with open(output, "w", encoding="utf-8") as f:
            f.write(report)
        console.print(f"\n[green]Report saved to {output}[/green]")


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--provider", "-p", default="anthropic")
@click.option("--model", "-m", default=None)
@click.option("--reviewers", "-n", default=3)
def verify(file, provider, model, reviewers):
    """Verify a document/paper using the 5-Axis framework.

    Alias for 'review --type paper' with stricter verification focus.
    """
    console.print(f"\n[bold]CCR Verify[/bold]: {file}")
    console.print(f"Mode: 5-Axis Verification | Reviewers: {reviewers}\n")

    with console.status("[bold green]Running 5-axis verification..."):
        reviewer = CCRReviewer(
            provider=provider,
            model=model,
            num_reviewers=reviewers,
        )
        result = reviewer.review_file(file, artifact_type="paper")

    _display_results(result)


@main.command()
def models():
    """Show supported models and their pricing."""
    from ccr.backends import PRICING

    table = Table(title="Supported Models & Pricing")
    table.add_column("Model", style="bold")
    table.add_column("Input ($/1M tok)", justify="right")
    table.add_column("Output ($/1M tok)", justify="right")
    table.add_column("~Cost per review*", justify="right", style="green")

    for model_name, prices in PRICING.items():
        # Estimate: 23K input + 8K output per review (3 reviewers + director)
        est = 23000 * prices["input"] / 1_000_000 + 8000 * prices["output"] / 1_000_000
        table.add_row(
            model_name,
            f"${prices['input']:.2f}",
            f"${prices['output']:.2f}",
            f"${est:.3f}",
        )

    console.print(table)
    console.print("\n[dim]* Estimated for a typical file (~200 lines, 3 reviewers)[/dim]")


def _display_results(result):
    """Display review results with rich formatting."""
    if not result.findings:
        console.print(Panel("[green bold]No issues found!", title="CCR Result"))
        return

    table = Table(title=f"CCR Review Results - {result.artifact_path}")
    table.add_column("", width=2)
    table.add_column("Severity", width=10)
    table.add_column("Axis", width=6)
    table.add_column("Location", width=20)
    table.add_column("Description")
    table.add_column("Consensus", width=10, justify="center")

    for f in result.findings:
        consensus = ""
        if len(f.agreed_by) >= 2:
            consensus = f"[green bold]★ {len(f.agreed_by)}[/green bold]"
        elif f.agreed_by:
            consensus = f"{len(f.agreed_by)}"

        style = SEVERITY_COLORS.get(f.severity, "")
        table.add_row(
            SEVERITY_EMOJI.get(f.severity, ""),
            f"[{style}]{f.severity.value}[/{style}]",
            f.axis.name,
            f.location,
            f.description,
            consensus,
        )

    console.print(table)

    # Summary
    console.print(f"\n  Total: {len(result.findings)} findings "
                  f"({result.critical_count} critical, {result.major_count} major)")
    console.print(f"  Consensus (★): {len(result.consensus_findings)} findings "
                  f"agreed by 2+ reviewers")
    console.print(f"  Cost: ${result.estimated_cost_usd:.4f} "
                  f"({result.total_tokens:,} tokens)")


def _format_report(result) -> str:
    """Format results as a plain text report."""
    lines = [
        "# CCR Review Report",
        f"File: {result.artifact_path}",
        f"Model: {result.model}",
        f"Reviewers: {result.num_reviewers}",
        f"Cost: ${result.estimated_cost_usd:.4f}",
        "",
        "## Findings",
        "",
    ]

    for f in result.findings:
        consensus = " ★" if len(f.agreed_by) >= 2 else ""
        lines.append(
            f"[{f.severity.value.upper()}] {f.axis.name} | {f.location} | "
            f"{f.description}{consensus}"
        )
        if f.suggestion:
            lines.append(f"  → {f.suggestion}")
        lines.append("")

    lines.append(f"\nTotal: {len(result.findings)} findings")
    lines.append(f"Consensus: {len(result.consensus_findings)}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
