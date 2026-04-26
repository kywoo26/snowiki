from __future__ import annotations

import click

from snowiki.cli.commands.benchmark import command as benchmark_command
from snowiki.cli.commands.benchmark_fetch import command as benchmark_fetch_command
from snowiki.cli.commands.export import command as export_command
from snowiki.cli.commands.fileback import command as fileback_command
from snowiki.cli.commands.ingest import command as ingest_command
from snowiki.cli.commands.lint import command as lint_command
from snowiki.cli.commands.mcp import command as mcp_command
from snowiki.cli.commands.prune import command as prune_command
from snowiki.cli.commands.query import command as query_command
from snowiki.cli.commands.rebuild import command as rebuild_command
from snowiki.cli.commands.recall import command as recall_command
from snowiki.cli.commands.status import command as status_command
from snowiki.cli.context import ensure_snowiki_context


@click.group(
    name="snowiki",
    context_settings={
        "default_map": {},
        "help_option_names": ["-h", "--help"],
        "max_content_width": 100,
    },
    short_help="Snowiki CLI-first runtime contract.",
)
@click.version_option(package_name="snowiki")
@click.pass_context
def app(ctx: click.Context) -> None:
    """Snowiki CLI-first runtime contract."""

    ensure_snowiki_context(ctx)


app.add_command(ingest_command)
app.add_command(rebuild_command)
app.add_command(query_command)
app.add_command(recall_command)
app.add_command(status_command)
app.add_command(lint_command)
app.add_command(export_command)
app.add_command(fileback_command)
app.add_command(prune_command)
app.add_command(benchmark_command)
app.add_command(benchmark_fetch_command)
app.add_command(mcp_command)


if __name__ == "__main__":
    app()
