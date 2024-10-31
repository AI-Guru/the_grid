import os
from langchain_openai import ChatOpenAI
from langchain_openai import AzureChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate


# Function to get a model.
def get_model(model_provider, model_name, temperature=0.5):
    """
    Get a model.
    :param model_provider: The model provider.
    :param model_name: The model name.
    :param temperature: The temperature.
    :return: The model.
    """

    assert isinstance(model_provider, str)
    assert isinstance(model_name, str)

    def raise_if_not_set(environment_variables):
        for env_var in environment_variables:
            if env_var not in os.environ:
                raise ValueError(f"{env_var} environment variable is not set.")

    if model_provider == "openai":
        raise_if_not_set(["OPENAI_API_KEY"])
        return ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name=model_name,
            temperature=temperature,
        )
    elif model_provider == "azure":
        raise_if_not_set(["AZURE_OPENAI_KEY", "AZURE_OPENAI_VERSION", "AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_BASE"])
        return AzureChatOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_VERSION"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            azure_endpoint=os.getenv("AZURE_OPENAI_BASE"),
            # model_name=model_name,
            temperature=temperature,
        )
    elif model_provider == "ollama":
        return ChatOpenAI(
            base_url="http://localhost:11434/v1" if "OLLAMA_OPENAI_BASE" not in os.environ else os.getenv("OLLAMA_OPENAI_BASE"),
            api_key="ollama",
            model_name=model_name,
            temperature=temperature,
        )
    elif model_provider == "anthropic":
        raise_if_not_set(["ANTHROPIC_API_KEY"])
        return ChatAnthropic(
            model=model_name,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=temperature,
            max_tokens=8192,
        )
    else:
        raise ValueError(f"Model provider {model_provider} not supported.")