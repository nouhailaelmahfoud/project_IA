import os

from dotenv import load_dotenv

load_dotenv()


def get_llm(provider: str = "openrouter", model: str = None,
            temperature: float = 0):
    """Renvoie le modèle de langage choisi : 'openrouter' ou 'ollama'."""
    if provider == "openrouter":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or os.environ["OPENROUTER_MODEL"],
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
            temperature=temperature,
            max_retries=1,  # limite les essais pour ménager les 50 requêtes
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model or os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:3b"),
            temperature=temperature,
        )
    raise ValueError(f"Moteur inconnu : {provider} (openrouter ou ollama)")