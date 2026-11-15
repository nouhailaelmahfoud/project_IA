import os

from dotenv import load_dotenv

load_dotenv()


def get_llm(provider: str = "openrouter", model: str = None,
            temperature: float = 0):
    """Renvoie le modèle de langage choisi : 'openrouter' ou 'ollama'."""
    if provider == "openrouter":
        from langchain_openai import ChatOpenAI

        options = {}
        effort = os.environ.get("OPENROUTER_REASONING_EFFORT", "low")
        if effort:
            # Limite la « réflexion » cachée des modèles de raisonnement
            options["extra_body"] = {"reasoning": {"effort": effort}}

        return ChatOpenAI(
            model=model or os.environ["OPENROUTER_MODEL"],
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
            temperature=temperature,
            max_retries=1,    # limite les essais pour ménager les 50 requêtes
            max_tokens=int(os.environ.get("OPENROUTER_MAX_TOKENS", "12000")),
            timeout=180,
            **options,
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model or os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:3b"),
            temperature=temperature,
            num_ctx=8192,      # taille de lecture : le fichier ne doit pas être coupé
            num_predict=1500,  # réponses courtes : on ne demande que des modifications ciblées
        )
    raise ValueError(f"Moteur inconnu : {provider} (openrouter ou ollama)")
