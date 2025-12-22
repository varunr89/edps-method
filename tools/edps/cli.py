"""EDPS Method CLI - Main entry point."""
import typer

from edps.commands.init import init as init_command

app = typer.Typer(
    name="edps",
    help="EDPS Method automation CLI",
    no_args_is_help=True,
)


@app.command()
def version():
    """Show version."""
    typer.echo("edps v0.1.0")


app.command(name="init")(init_command)


if __name__ == "__main__":
    app()
