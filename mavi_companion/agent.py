import keyring
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

def get_api_key(model: str) -> str | None:
    key_name = f"MAVI_COMPANION_MODEL_{model}"
    return keyring.get_password(key_name, model)

def get_llm(model: str) -> Runnable | None:
    api_key = get_api_key(model)
    if not api_key:
        print(f"API key for model '{model}' not found.")
        return None

    if model == "gemini-2.5-flash":
        return ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
    elif model == "openai":
        return ChatOpenAI(model="gpt-5-nano", api_key=api_key)
    else:
        print(f"Model '{model}' is not supported.")
        return None

def create_agent_with_memory(model: str, agent_name: str = "mavi_agent") -> Runnable | None:
    llm = get_llm(model)
    if not llm:
        return None
    agent = create_agent(
        model=llm,
        name=agent_name   
    )
    return agent

if __name__ == "__main__":
    model_name = "gemini-2.5-flash"
    agent = create_agent_with_memory(model_name)
    if agent:
        print(f"Agent for model '{model_name}' created successfully!")
    else:
        print(f"Failed to create agent for model '{model_name}'.")
