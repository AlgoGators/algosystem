import click
from algosystem.utils.config import config_UI

@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument(
    "config_path",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    metavar="PATH",
)
def cli(config_path):
    """
    Launch the configuration UI for the given JSON file.

    PATH  Path to your config file (must exist).
    """
    config_UI(config_path)

if __name__ == "__main__":
    cli()
