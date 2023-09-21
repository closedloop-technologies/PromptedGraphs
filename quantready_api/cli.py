import pyfiglet
from rich import print
from typer import Typer

from quantready_api import __description__ as DESCRIPTION
from quantready_api import __name__ as NAME
from quantready_api import __version__ as VERSION
from quantready_api.config import load_config


def banner():
    return pyfiglet.figlet_format(NAME.replace("_", " ").title(), font="slant").rstrip()


app = Typer(help=f"{(NAME or '').replace('_', ' ').title()} CLI")


@app.command()
def info():
    """Prints info about the package"""
    print(f"{banner()}\n")
    print(f"{NAME}: {DESCRIPTION}")
    print(f"Version: {VERSION}\n")
    print(load_config())


@app.command()
def main():
    """Main Function"""
    print(f"{banner()}\n")
    print(
        "This is your default command-line interface.  Feel free to customize it as you see fit.\n"
    )
