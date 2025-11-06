import typer
from rich.console import Console
from rich.table import Table
import keyring
from .agent import get_agent
from rich.console import Console
from rich.spinner import Spinner
from time import sleep

console = Console()
app = typer.Typer(help="Mavi Companion CLI - Coding assistant with model selection & key management.")

models = [["TinyLlama-1.1B-Chat-v1.0", "LOCAL"], ["gemini-2.5-flash", "CLOUD"]]
KEYRING_PREFIX = "MAVI_COMPANION_MODEL_"

def normalize_content(value) -> str:
    """Coerce various response content types (str/list/dict/objects) into a string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if hasattr(value, "content") and not isinstance(value, dict):
        try:
            return normalize_content(getattr(value, "content"))
        except Exception:
            pass
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                parts.append(str(text) if text is not None else "")
            else:
                text_attr = getattr(item, "text", None)
                if text_attr is not None:
                    parts.append(str(text_attr))
                else:
                    content_attr = getattr(item, "content", None)
                    parts.append(str(content_attr) if content_attr is not None else str(item))
        return "".join([p for p in parts if p])
    if isinstance(value, dict):
        if "content" in value:
            return normalize_content(value.get("content"))
        if "text" in value:
            return str(value.get("text", ""))
        return str(value)
    return str(value)

def add_key(model: str) -> None:
    model_type = next((m[1] for m in models if m[0] == model), None)
    if model_type != "CLOUD":
        console.print(f"[yellow]No API key required for local model '{model}'.[/yellow]")
        return

    existing = keyring.get_password(f"{KEYRING_PREFIX}{model}", model)
    if existing:
        console.print(f"[red]API key for '{model}' already exists.[/red]")
        return

    key = typer.prompt(f"Enter API key for '{model}'", hide_input=True)
    if key:
        keyring.set_password(f"{KEYRING_PREFIX}{model}", model, key)
        console.print(f"[green]Saved API key for '{model}'.[/green]")
    else:
        console.print("[red]No key entered. Nothing saved.[/red]")


def get_key(model: str) -> str | None:
    model_type = next((m[1] for m in models if m[0] == model), None)
    if model_type != "CLOUD":
        return None
    return keyring.get_password(f"{KEYRING_PREFIX}{model}", model)


def delete_key(model: str) -> None:
    model_type = next((m[1] for m in models if m[0] == model), None)
    if model_type != "CLOUD":
        console.print(f"[yellow]No API key stored for local model '{model}'.[/yellow]")
        return

    try:
        keyring.delete_password(f"{KEYRING_PREFIX}{model}", model)
        console.print(f"[green]Deleted API key for '{model}'.[/green]")
    except keyring.errors.PasswordDeleteError:
        console.print(f"[red]No API key found for '{model}'.[/red]")


def select_model() -> str:
    console.print("\n[bold cyan]Available Models:[/bold cyan]")
    for idx, (name, mtype) in enumerate(models, start=1):
        console.print(f"{idx}. {name} [{mtype}]")

    while True:
        choice = typer.prompt("Select a model by number or name", default=models[0][0])
        if choice.isdigit() and 1 <= int(choice) <= len(models):
            return models[int(choice) - 1][0]
        elif choice in [m[0] for m in models]:
            return choice
        else:
            console.print("[red]Invalid choice. Try again.[/red]")

@app.command(help="Start an interactive coding assistant session.")
def chat():
    console.print('''
███╗   ███╗ █████╗ ██╗   ██╗██╗
████╗ ████║██╔══██╗██║   ██║██║
██╔████╔██║███████║██║   ██║██║
██║╚██╔╝██║██╔══██║╚██╗ ██╔╝██║
██║ ╚═╝ ██║██║  ██║ ╚████╔╝ ██║
╚═╝     ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝
                               
 ██████╗██╗     ██╗            
██╔════╝██║     ██║            
██║     ██║     ██║            
██║     ██║     ██║            
╚██████╗███████╗██║            
 ╚═════╝╚══════╝╚═╝                                                     
    ''')

    agent = None
    model = None
    while not agent:
        model = select_model()
        console.print(f"\n[bold cyan]Initializing model:[/bold cyan] {model}\n")
        agent = get_agent(model)
        if not agent:
            console.print(f"[red]Failed to initialize model '{model}'. Try again.[/red]")

    console.print(f"[green]Model '{model}' is ready![/green]")
    console.print("Type '--model' anytime to switch models.")
    console.print("Type 'exit' or 'quit' to leave.\n")

    messages = []

    while True:
        user_input = typer.prompt("You")

        if user_input.lower() in ["exit", "quit"]:
            console.print('\n[bold red]Goodbye![/bold red]')
            break

        if user_input.strip().lower() == "--model":
            agent = None
            while not agent:
                model = select_model()
                console.print(f"\n[bold cyan]Reinitializing model:[/bold cyan] {model}\n")
                agent = get_agent(model)
                if not agent:
                    console.print(f"[red]Failed to initialize model '{model}'. Try again.[/red]")
            console.print(f"[green]Switched to model '{model}'.[/green]\n")
            continue

        messages.append({"role": "user", "content": user_input})

        payload = {"messages": messages}

        assistant_response = ""

        try:
            with console.status("[bold blue]Bot is thinking...[/bold blue]", spinner="dots"):
                response = agent.invoke(payload)
                latest_msg = None
                if isinstance(response, dict) and "messages" in response:
                    resp_messages = response.get("messages") or []
                    latest_msg = resp_messages[-1] if resp_messages else None
                elif hasattr(response, "messages"):
                    resp_messages = getattr(response, "messages", [])
                    latest_msg = resp_messages[-1] if resp_messages else None
                else:
                    latest_msg = response

                assistant_response = normalize_content(getattr(latest_msg, "content", latest_msg))

            console.print(f"[bold blue]Bot:[/bold blue] {assistant_response}\n")

            if assistant_response:
                messages.append({"role": "assistant", "content": assistant_response})

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}\n")


@app.command(help="Manage API keys for cloud models.")
def keys(
    set_key: bool = typer.Option(False, "--set", help="Set an API key"),
    delete: bool = typer.Option(False, "--delete", help="Delete an API key"),
):
    if set_key:
        console.print("Available cloud models:\n")
        for name, mtype in models:
            if mtype == "CLOUD":
                console.print(f"- {name}")
        model = typer.prompt("Enter model name")
        add_key(model)
        raise typer.Exit()

    if delete:
        console.print("Available cloud models:\n")
        for name, mtype in models:
            if mtype == "CLOUD":
                console.print(f"- {name}")
        model = typer.prompt("Enter model name")
        delete_key(model)
        raise typer.Exit()

    table = Table(title="Model API Key Status", show_lines=True)
    table.add_column("Model", style="bold cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Key Status", style="yellow")

    for name, mtype in models:
        key = get_key(name)
        status = "[green]Available[/green]" if key else "[red]Missing[/red]"
        table.add_row(name, mtype, status)

    console.print(table)


@app.command(help="Ask a single coding question directly.")
def ask(query: str):
    agent = None
    model = None

    while not agent:
        model = select_model()
        console.print(f"\n[bold cyan]Initializing model:[/bold cyan] {model}\n")
        agent = get_agent(model)
        if not agent:
            console.print(f"[red]Failed to initialize model '{model}'. Try again.[/red]")

    try:
        payload = {"messages": [{"role": "user", "content": query}]}
        response = agent.invoke(payload)
        latest_msg = None
        if isinstance(response, dict) and "messages" in response:
            resp_messages = response.get("messages") or []
            latest_msg = resp_messages[-1] if resp_messages else None
        else:
            latest_msg = response
        output = normalize_content(getattr(latest_msg, "content", latest_msg))
        console.print(f"[bold blue]Bot:[/bold blue] {output}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


if __name__ == "__main__":
    app()
