## Mavi Companion (QA Chatbot CLI)

Simple command-line companion for quick Q&A and documentation lookups. Provides an interactive chat and a one-shot question command. API keys are stored securely using the system keyring.

### Requirements
- Python 3.9+
- macOS, Linux, or Windows

### Install
In a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -e .
```

Alternatively, install from the built distribution in `dist/`:

```bash
pip install dist/mavi_companion-0.1.0-py3-none-any.whl
```

This installs the CLI commands `mavi` and `mavi-companion`.

### Configure API Keys
Set an API key for one of the supported models: `gemini-2.5-flash`, `openai`, `deepseek`.

```bash
mavi keys --set
```

Notes:
- Keys are saved in your system keyring (e.g., macOS Keychain).
- If a key already exists and you want to change it, delete it first:

```bash
mavi keys --delete
```

List current key status:

```bash
mavi keys
```

### Usage
- Start interactive chat:

```bash
mavi chat
```

- Ask a one-off question:

```bash
mavi ask "How do I create a virtual environment?"
```

During chat you can type `--model` to switch between available models for which you have set keys.

### Uninstall

```bash
pip uninstall mavi-companion
```

### Development
- Run the app directly:

```bash
python -m mavi_companion.main --help
```

- CLI help:

```bash
mavi --help
```


