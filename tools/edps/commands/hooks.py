"""Hooks command - install git hooks."""
import stat
from pathlib import Path

import typer
from rich.console import Console

console = Console()

HOOK_SCRIPT = '''#!/bin/bash
set -e

# Get staged files
STAGED=$(git diff --cached --name-only)

if [ -z "$STAGED" ]; then
    exit 0
fi

# Run progress sync on staged files
MODIFIED=$(python -m edps.progress --hook <<< "$STAGED" 2>/dev/null || true)

# Auto-stage any modified progress files
if [ -n "$MODIFIED" ]; then
    echo "$MODIFIED" | while read -r file; do
        if [ -n "$file" ] && [ -f "$file" ]; then
            git add "$file"
            echo "Auto-staged: $file"
        fi
    done
fi
'''


def init_hooks(
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Overwrite existing pre-commit hook",
    ),
) -> None:
    """Install the EDPS pre-commit hook."""
    # Find .git directory
    git_dir = Path.cwd() / ".git"
    if not git_dir.exists():
        console.print("[red]Error:[/red] Not a git repository")
        raise typer.Exit(1)

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hook_path = hooks_dir / "pre-commit"

    if hook_path.exists() and not force:
        console.print(f"[yellow]Warning:[/yellow] {hook_path} already exists")
        console.print("Use --force to overwrite")
        raise typer.Exit(1)

    # Write hook
    hook_path.write_text(HOOK_SCRIPT)

    # Make executable
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    console.print(f"[green]✓[/green] Installed pre-commit hook: {hook_path}")
    console.print("[dim]Progress will auto-sync on each commit[/dim]")
