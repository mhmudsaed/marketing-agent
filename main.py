"""CLI entry point for the Marketing Content Pipeline Agent."""
import sys
import asyncio
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from core.pipeline import MarketingPipeline
from config.settings import settings
from utils.logger import logger

console = Console()

def print_banner():
    """Print application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║         🚀 MARKETING CONTENT PIPELINE AGENT 🚀               ║
║                                                              ║
║    AI-Powered Marketing Agency in a Box                      ║
║    Research → Strategy → Content → Verification              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")

def validate_settings():
    """Validate required configuration."""
    errors = settings.validate()
    if errors:
        console.print("[bold red]❌ Configuration Errors:[/bold red]")
        for error in errors:
            console.print(f"  • {error}")
        console.print("\n[yellow]Please set the required environment variables or update .env[/yellow]")
        sys.exit(1)

def print_results(result: dict):
    """Print pipeline results in a beautiful format."""
    console.print()
    console.print(Panel(
        f"[bold green]✅ Pipeline Complete[/bold green]\n"
        f"Session ID: [cyan]{result['session_id']}[/cyan]\n"
        f"Output: [cyan]{result['output_dir']}[/cyan]",
        title="Results",
        border_style="green"
    ))
    
    # Research summary
    research = result.get("research")
    if research:
        console.print(Panel(
            f"[bold]{research.business.name}[/bold]\n"
            f"{research.business.description[:150]}...\n\n"
            f"Industry: {research.business.industry}\n"
            f"Niche: {research.business.niche}\n"
            f"Confidence: {research.confidence_score:.0%}",
            title="[bold blue]📊 Research[/bold blue]",
            border_style="blue"
        ))
    
    # Strategy summary
    strategy = result.get("strategy")
    if strategy:
        console.print(Panel(
            f"Pillars: {len(strategy.pillars)} | "
            f"Channels: {len(strategy.channels)} | "
            f"Posts: {len(strategy.calendar)}\n\n"
            f"Strategy: {strategy.overall_strategy[:120]}...",
            title="[bold magenta]📋 Strategy[/bold magenta]",
            border_style="magenta"
        ))
    
    # Verification summary
    verification = result.get("verification")
    if verification:
        table = Table(title="Verification Results", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Checked", str(verification.total_checked))
        table.add_row("Passed", f"[green]{verification.total_passed}[/green]")
        table.add_row("Failed", f"[red]{verification.total_failed}[/red]")
        table.add_row("Auto-Modified", f"[yellow]{verification.total_modified}[/yellow]")
        table.add_row("Rejected", f"[red]{verification.total_rejected}[/red]")
        table.add_row("Average Score", f"[bold]{verification.average_score:.2f}/1.0[/bold]")
        
        console.print(table)
        
        if verification.critical_issues:
            console.print("[bold red]⚠️ Critical Issues:[/bold red]")
            for issue in verification.critical_issues:
                console.print(f"  • {issue}")

async def main():
    """Main async entry point."""
    parser = argparse.ArgumentParser(
        description="Marketing Content Pipeline Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --url https://example.com
  python main.py --url https://example.com --research-only
  python main.py --url https://example.com --model anthropic/claude-3-opus
        """
    )
    
    parser.add_argument(
        "--url", "-u",
        required=True,
        help="Business website URL to analyze"
    )
    parser.add_argument(
        "--model", "-m",
        default=settings.OPENROUTER_MODEL,
        help=f"OpenRouter model to use (default: {settings.OPENROUTER_MODEL})"
    )
    parser.add_argument(
        "--research-only",
        action="store_true",
        help="Run only the research phase"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=str(settings.OUTPUT_DIR),
        help="Output directory for results"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Update settings from args
    if args.model:
        settings.OPENROUTER_MODEL = args.model
    if args.output_dir:
        settings.OUTPUT_DIR = Path(args.output_dir)
    
    # Validate
    validate_settings()
    
    # Print banner
    print_banner()
    
    console.print(f"[bold]Target:[/bold] {args.url}")
    console.print(f"[bold]Model:[/bold] {settings.OPENROUTER_MODEL}")
    console.print(f"[bold]Output:[/bold] {settings.OUTPUT_DIR}")
    console.print()
    
    # Run pipeline
    try:
        async with MarketingPipeline() as pipeline:
            if args.research_only:
                research = await pipeline.run_research_only(args.url)
                console.print(Panel(
                    f"[bold]{research.business.name}[/bold]\n"
                    f"{research.summary}\n\n"
                    f"Confidence: {research.confidence_score:.0%}",
                    title="Research Complete",
                    border_style="green"
                ))
            else:
                result = await pipeline.run(args.url)
                print_results(result)
                
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]❌ Fatal error: {e}[/bold red]")
        logger.exception("Pipeline failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
