# algosystem/cli/commands.py

import click
from algosystem.utils.decorators import expose, get_exposed

@expose
def my_command():
    """Example command exposed via a decorator."""
    # Your business logic here.
    return "Command Executed!"

@click.command()
def cli():
    """CLI entry point that runs an exposed command."""
    # In a more complex setup, you might iterate over all exposed functions.
    result = my_command()  # or choose based on some CLI argument
    click.echo(result)

if __name__ == "__main__":
    cli()
