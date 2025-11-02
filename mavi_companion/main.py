import os
import typer
import keyring
from rich.console import Console
from rich.table import Table

console = Console()
app = typer.Typer(help="Mavi Companion CLI - fast coding assistant for documentation lookups.")

ALLOWED_MODELS = ["gemini-2.5-flash", "openai", "deepseek"]
KEYRING_PREFIX = "MAVI_COMPANION_MODEL_"

current_model = None

def select_model(available_models):
    """Prompt user to select a model and return the selected model."""
    console.print("Available Models with API keys:")
    for idx, model in enumerate(available_models, start=1):
        console.print(f"{idx}. {model}")

    while True:
        choice = typer.prompt(f"Select a model [default: {available_models[0]}]")
        if choice == "":
            return available_models[0]
        if choice.isdigit() and (1 <= int(choice) <= len(available_models)):
            return available_models[int(choice) - 1]
        elif choice in available_models:
            return choice
        else:
            console.print("[red]Invalid choice, try again.[/red]")

@app.command(help="Start an interactive chat session with the bot.")
def chat():
    global current_model

    available_models = [model for model in ALLOWED_MODELS if keyring.get_password(f"{KEYRING_PREFIX}{model}", model)]
    if not available_models:
        console.print("[bold red]No API keys found. Please set at least one API key using the 'keys --set' command.[/bold red]")
        raise typer.Exit()

    console.print('''
███╗   ███╗ █████╗ ██╗   ██╗██╗                                             
████╗ ████║██╔══██╗██║   ██║██║                                             
██╔████╔██║███████║██║   ██║██║                                             
██║╚██╔╝██║██╔══██║╚██╗ ██╔╝██║                                             
██║ ╚═╝ ██║██║  ██║ ╚████╔╝ ██║                                             
╚═╝     ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝                                             
    ''')

    current_model = select_model(available_models)
    console.print(f"[bold green]Using model: {current_model}[/bold green]")
    console.print("Type 'exit' or 'quit' to leave. Type '--model' to switch models.\n")

    while True:
        user_input = typer.prompt("You")
        if user_input.lower() in ["exit", "quit"]:
            console.print('\n')
            console.print("[bold red]Shutting Down![/bold red]")
            break

        if user_input.lower() == "--model":
            current_model = select_model(available_models)
            console.print(f"[bold green]Switched to model: {current_model}[/bold green]")
            continue

        bot_response = f"I heard you say: {user_input} (using model {current_model})"
        console.print(f"[bold blue]Bot:[/bold blue] {bot_response}")

@app.command(help="Manage API keys for allowed models. You can list, set, or delete keys.")
def keys(
    set_key: bool = typer.Option(False, "--set", help="Set an API key for a model"),
    delete_key: bool = typer.Option(False, "--delete", help="Delete an API key for a model"),
):
    """
    Manage API keys for allowed models.
    By default, lists all models and their API key status.
    """
    if set_key:
        console.print("Select a model to set the API key:")
        for idx, model_name in enumerate(ALLOWED_MODELS, start=1):
            console.print(f"{idx}. {model_name}")

        while True:
            choice = typer.prompt("Enter the number of the model")
            if not choice.isdigit() or not (1 <= int(choice) <= len(ALLOWED_MODELS)):
                console.print("[red]Invalid choice, please try again.[/red]")
                continue
            model = ALLOWED_MODELS[int(choice) - 1]
            break

        key_name = f"{KEYRING_PREFIX}{model}"
        existing_key = keyring.get_password(key_name, model)
        if existing_key:
            console.print(f"[yellow]API key for {model} is already set and cannot be changed.[/yellow]")
            raise typer.Exit()

        key = typer.prompt(f"Enter API key for {model}", hide_input=True)
        keyring.set_password(key_name, model, key)
        console.print(f"[green]Saved API key for {model}[/green]")
        raise typer.Exit()

    if delete_key:
        console.print("Select a model to delete the API key:")
        for idx, model_name in enumerate(ALLOWED_MODELS, start=1):
            console.print(f"{idx}. {model_name}")

        while True:
            choice = typer.prompt("Enter the number of the model")
            if not choice.isdigit() or not (1 <= int(choice) <= len(ALLOWED_MODELS)):
                console.print("[red]Invalid choice, please try again.[/red]")
                continue
            model = ALLOWED_MODELS[int(choice) - 1]
            break

        key_name = f"{KEYRING_PREFIX}{model}"
        try:
            keyring.delete_password(key_name, model)
            console.print(f"[yellow]Deleted API key for {model}[/yellow]")
        except keyring.errors.PasswordDeleteError:
            console.print(f"[red]No API key found for {model}[/red]")
        raise typer.Exit()

    table = Table(title="Models and API Key Status", show_lines=True)
    table.add_column("Model Name", style="bold cyan")
    table.add_column("API Key Status", style="yellow")

    for model in ALLOWED_MODELS:
        key_name = f"{KEYRING_PREFIX}{model}"
        key = keyring.get_password(key_name, model)
        status = "[green]Available[/green]" if key else "[red]Missing[/red]"
        table.add_row(model, status)

    console.print(table)

@app.command(help="Ask a question to the bot directly from the command line.")
def ask(query: str):
    typer.echo(f"You Asked: {query} (using model {current_model})")


if __name__ == "__main__":
    app()