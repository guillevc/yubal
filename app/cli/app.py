"""Typer app instance."""
import typer
import typer.main


def _help_all_callback(ctx: typer.Context, value: bool) -> None:
    """Print help for all commands."""
    if not value:
        return

    click = typer.main.click
    click_app = ctx.command
    for name in sorted(click_app.commands.keys()):
        cmd = click_app.commands[name]
        with click.Context(cmd, info_name=f"ytadl {name}") as cmd_ctx:
            typer.echo(cmd.get_help(cmd_ctx))
    raise typer.Exit()


app = typer.Typer(
    name="ytadl",
    help="YouTube Album Downloader - Download and organize music from YouTube",
    no_args_is_help=True,
)


@app.callback()
def _main_callback(
    ctx: typer.Context,
    help_all: bool = typer.Option(
        False,
        "--help-all",
        callback=_help_all_callback,
        is_eager=True,
        help="Show help for all commands",
    ),
) -> None:
    """YouTube Album Downloader - Download and organize music from YouTube."""
    pass
