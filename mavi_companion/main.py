import os
import typer
import keyring
from rich.console import Console
from rich.table import Table
from mavi_companion.agent import create_agent_with_memory 

console = Console()
app = typer.Typer(help="Mavi Companion CLI - fast coding assistant for documentation lookups.")

ALLOWED_MODELS = ["gemini-2.5-flash", "openai"]
ALLOWED_TOOLS = ["tavily"]
KEYRING_PREFIX_MODEL = "MAVI_COMPANION_MODEL_"
KEYRING_PREFIX_TOOL = "MAVI_COMPANION_TOOL_"

current_model = None
current_agent = None

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

def init_agent(model_name: str):
    """Initialize the agent for the selected model."""
    global current_agent
    agent = create_agent_with_memory(model_name)
    if agent:
        current_agent = agent
        console.print(f"[bold green]Agent initialized for model: {model_name}[/bold green]")
    else:
        console.print(f"[bold red]Failed to initialize agent for model: {model_name}[/bold red]")

@app.command(help="Start an interactive chat session with the bot.")
def chat():
    global current_model, current_agent

    available_models = [
        model for model in ALLOWED_MODELS
        if keyring.get_password(f"{KEYRING_PREFIX_MODEL}{model}", model)
    ]
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
    init_agent(current_model)
    console.print("Type 'exit' or 'quit' to leave. Type '--model' to switch models.\n")

    while True:
        bot_response = ""
        user_input = typer.prompt("You")
        if user_input.lower() in ["exit", "quit"]:
            console.print('\n[bold red]Shutting Down![/bold red]')
            break

        if user_input.lower() == "--model":
            current_model = select_model(available_models)
            init_agent(current_model)
            continue

        if current_agent:
            try:
                response = current_agent.invoke({"messages": [{"role": "user", "content": user_input}]})
                bot_response = response['messages'][-1].content
            except Exception as e:
                print(e)
        else:
            bot_response = f"[red]No agent initialized for model {current_model}[/red]"

        console.print(f"[bold blue]Bot:[/bold blue] {bot_response}")

@app.command(help="Manage API keys for models and tools together.")
def keys(
    set_key: bool = typer.Option(False, "--set", help="Set an API key for a model or tool"),
    delete_key: bool = typer.Option(False, "--delete", help="Delete an API key for a model or tool"),
):
    all_items = [
        *[(name, "model", KEYRING_PREFIX_MODEL) for name in ALLOWED_MODELS],
        *[(name, "tool", KEYRING_PREFIX_TOOL) for name in ALLOWED_TOOLS],
    ]

    if set_key:
        console.print("Select an item to set its API key:\n")
        for idx, (name, category, _) in enumerate(all_items, start=1):
            console.print(f"{idx}. {name} [{category}]")

        while True:
            choice = typer.prompt("Enter the number")
            if not choice.isdigit() or not (1 <= int(choice) <= len(all_items)):
                console.print("[red]Invalid choice, please try again.[/red]")
                continue
            name, category, prefix = all_items[int(choice) - 1]
            break

        key_name = f"{prefix}{name}"
        existing_key = keyring.get_password(key_name, name)
        if existing_key:
            console.print(f"[yellow]API key for {category} '{name}' is already set and cannot be changed.[/yellow]")
            raise typer.Exit()

        key = typer.prompt(f"Enter API key for {category} '{name}'", hide_input=True)
        keyring.set_password(key_name, name, key)
        console.print(f"[green]Saved API key for {category} '{name}'[/green]")
        raise typer.Exit()

    if delete_key:
        console.print("Select an item to delete its API key:\n")
        for idx, (name, category, _) in enumerate(all_items, start=1):
            console.print(f"{idx}. {name} [{category}]")

        while True:
            choice = typer.prompt("Enter the number")
            if not choice.isdigit() or not (1 <= int(choice) <= len(all_items)):
                console.print("[red]Invalid choice, please try again.[/red]")
                continue
            name, category, prefix = all_items[int(choice) - 1]
            break

        key_name = f"{prefix}{name}"
        try:
            keyring.delete_password(key_name, name)
            console.print(f"[yellow]Deleted API key for {category} '{name}'[/yellow]")
        except keyring.errors.PasswordDeleteError:
            console.print(f"[red]No API key found for {category} '{name}'[/red]")
        raise typer.Exit()

    table = Table(title="Models and Tools - API Key Status", show_lines=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Type", style="magenta")
    table.add_column("API Key Status", style="yellow")

    for name, category, prefix in all_items:
        key = keyring.get_password(f"{prefix}{name}", name)
        status = "[green]Available[/green]" if key else "[red]Missing[/red]"
        table.add_row(name, category, status)

    console.print(table)

@app.command(help="Ask a question to the bot directly from the command line.")
def ask(query: str):
    global current_agent, current_model

    available_models = [
        model for model in ALLOWED_MODELS
        if keyring.get_password(f"{KEYRING_PREFIX_MODEL}{model}", model)
    ]
    if not available_models:
        console.print("[bold red]No API keys found. Please set at least one API key using the 'keys --set' command.[/bold red]")
        raise typer.Exit()

    if not current_agent:
        current_model = select_model(available_models)
        init_agent(current_model)

    try:
        response = current_agent.invoke({"messages": [{"role": "user", "content": query}]})
        bot_response = response['messages'][-1].content
    except Exception as e:
        bot_response = f"[red]Error:[/red] {e}"

    console.print(f"[bold blue]Bot:[/bold blue] {bot_response}")


if __name__ == "__main__":
    app()
