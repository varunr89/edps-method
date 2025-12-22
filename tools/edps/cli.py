"""EDPS Method CLI - Main entry point."""
import typer

app = typer.Typer(
    name="edps",
    help="EDPS Method automation CLI",
    no_args_is_help=True,
)


@app.callback()
def callback():
    """EDPS Method automation CLI."""
    pass


@app.command()
def version():
    """Show version."""
    typer.echo("edps v0.1.0")


if __name__ == "__main__":
    app()
