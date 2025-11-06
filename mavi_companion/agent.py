from typing import List
import re
import keyring

from langchain.tools import tool
from langchain.chat_models import BaseChatModel
from langchain.agents import create_agent
from langchain.messages import SystemMessage
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.document_loaders import GithubFileLoader
from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents.middleware import LLMToolSelectorMiddleware
import requests

def detect_default_branch(owner: str, repo: str) -> str:
    try:
        resp = requests.get(f"https://api.github.com/repos/{owner}/{repo}")
        if resp.status_code == 200:
            return resp.json().get("default_branch", "main")
    except Exception:
        pass
    return "main"


KEYRING_PREFIX = "MAVI_COMPANION_MODEL_"

@tool("github-repo-docs", description="Search GitHub for repositories and fetch code/markdown files from the top repo.")
def get_github_repo_docs(query: str) -> List[dict]:
    """Search GitHub repos via DuckDuckGo and fetch coding files from the top repository."""
    try:
        pattern = re.compile(r"https?://github\.com/([^/]+)/([^/]+)(?:/|$)")
        search = DuckDuckGoSearchResults(output_format="list", max_results=15)
        results = search.invoke(f"site:github.com inurl:github.com {query} documentation OR readme OR api")

        def is_github_repo_url(url: str) -> bool:
            if "github.com" not in url:
                return False
            url = url.split('?', 1)[0].split('#', 1)[0]
            parts = url.replace("https://github.com/", "").strip("/").split("/")
            return len(parts) == 2 and all(parts)

        repo_urls = [item['link'] for item in results if is_github_repo_url(item['link'])]
        if not repo_urls:
            return [{"error": "No GitHub repositories found."}]

        url = repo_urls[0]
        match = pattern.match(url)
        if not match:
            return [{"error": "Invalid GitHub URL."}]

        owner, repo = match.group(1), match.group(2)
        branch = detect_default_branch(owner, repo)
        loader = GithubFileLoader(
            repo=f"{owner}/{repo}",
            branch=branch,
            access_token="your-github-api-key",
            file_filter=lambda file_path: file_path.endswith((
                ".md", ".py", ".js", ".ts", ".java", ".c", ".cpp", ".cs", ".go", ".rb",
                ".php", ".swift", ".rs", ".sh", ".html", ".css", ".json", ".yml", ".yaml"
            ))
        )
        documents = loader.load()
        output = [{"source": doc.metadata.get("source", ""), "content": doc.page_content} for doc in documents]

        print(f"Fetched {len(output)} documents from {owner}/{repo}")
        return output
    except Exception as e:
        print(f"Fetched 0 documents.")
        print(e)
        return "No Docs found."

def get_api_key(model: str) -> str | None:
    """Retrieve API key for cloud models from keyring."""
    if model == "gemini-2.5-flash":
        return keyring.get_password(f"{KEYRING_PREFIX}{model}", model)
    return None

def get_llm(model: str) -> BaseChatModel | None:
    """Return a LangChain-compatible chat model based on the model name."""
    if model == "TinyLlama-1.1B-Chat-v1.0":
        llm = HuggingFacePipeline.from_model_id(
            model_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            task="text-generation",
            pipeline_kwargs=dict(
                max_new_tokens=512,
                do_sample=False,
                repetition_penalty=1.03,
                return_full_text=False,
            ),
        )
        return ChatHuggingFace(llm=llm)

    elif model == "gemini-2.5-flash":
        api_key = get_api_key(model)
        if not api_key:
            print("Missing API key for Gemini. Please set it using your CLI.")
            return None
        return ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)

    else:
        print(f"Unsupported model: {model}")
        return None

def get_agent(model: str):
    """Create and return a LangChain agent with tools and system prompt."""
    chat_model = get_llm(model)
    if not chat_model:
        return None

    system_prompt = """
    You are a CLI-based coding assistant.
    Your job is to help users with programming, debugging, and explaining code clearly.
    Rules:
    - Keep responses concise (100–200 words).
    - Avoid unnecessary formatting or markdown.
    - Provide short, practical code snippets when needed.
    - Do not repeat explanations.
    - Write in a clean, readable terminal style.
    - Focus on clarity, not decoration.

    Docs from Github Repo is only for documentation don't prompt user to clone the repo.
    """

    agent = create_agent(
        model=chat_model,
        system_prompt=system_prompt,
        tools=[get_github_repo_docs],
        middleware=[
        LLMToolSelectorMiddleware(
            model=chat_model,
            max_tools=3,
            always_include=["github-repo-docs"],
            system_prompt=(
                "You are an intelligent tool selector. "
                "Always use the 'github-repo-docs' tool when user requests documentation, repositories, or code reference. "
                "Do not guess—only use tools relevant to the user's intent. "
                "for any coding question which is about web development AI or data science call this tool for js project specially"
                "Prefer concise reasoning and select at most 3 tools per query."
            )
        )]
    )
    return agent
