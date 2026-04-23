from __future__ import annotations

import click

from snowiki.cli.commands.benchmark import command as benchmark_command
from snowiki.cli.commands.daemon import command as daemon_command
from snowiki.cli.commands.export import command as export_command
from snowiki.cli.commands.fileback import command as fileback_command
from snowiki.cli.commands.ingest import command as ingest_command
from snowiki.cli.commands.lint import command as lint_command
from snowiki.cli.commands.mcp import command as mcp_command
from snowiki.cli.commands.query import command as query_command
from snowiki.cli.commands.rebuild import command as rebuild_command
from snowiki.cli.commands.recall import command as recall_command
from snowiki.cli.commands.status import command as status_command

app = click.Group(
    name="snowiki", context_settings={"help_option_names": ["-h", "--help"]}
)


app.add_command(ingest_command)
app.add_command(rebuild_command)
app.add_command(query_command)
app.add_command(recall_command)
app.add_command(status_command)
app.add_command(lint_command)
app.add_command(export_command)
app.add_command(fileback_command)
app.add_command(benchmark_command)
app.add_command(daemon_command)
app.add_command(mcp_command)


if __name__ == "__main__":
    app()
