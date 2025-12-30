from typing import Any, Dict

from smolagents.models import (
    InferenceClientModel,
    LiteLLMModel,
    OpenAIModel,
    TransformersModel,
    VLLMModel,
)


_PROVIDER_ALIAS = {
    "openai": "openai-server",
    "openai-server": "openai-server",
    "vllm": "vllm",
    "transformers": "transformers",
    "litellm": "litellm",
    "inference": "inference-client",
    "inference-client": "inference-client",
    "hf-inference": "inference-client",
}


def _resolve_provider(config: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    model_cfg = config.get("Model", {}) or {}
    provider_raw = model_cfg.get("provider")
    if not provider_raw:
        raise ValueError("Model provider is not specified in config under `Model.provider`.")

    provider_key = _PROVIDER_ALIAS.get(str(provider_raw).lower())
    if not provider_key:
        raise ValueError(f"Unsupported model provider '{provider_raw}'.")

    parameters = model_cfg.get("parameters", {}) or {}
    provider_settings = (model_cfg.get("providers") or {}).get(provider_raw) or {}
    merged = {**parameters, **provider_settings}
    if "model_id" not in merged:
        raise ValueError(f"`model_id` is required for provider '{provider_raw}'.")
    return provider_key, merged


def create_model(config: Dict[str, Any]):
    """
    Instantiate the smolagents model specified in the config.

    Supports providers: openai-server, vllm, transformers, litellm, inference-client.
    """
    provider, kwargs = _resolve_provider(config)

    if provider == "openai-server":
        return OpenAIModel(**kwargs)
    if provider == "vllm":
        return VLLMModel(**kwargs)
    if provider == "transformers":
        return TransformersModel(**kwargs)
    if provider == "litellm":
        return LiteLLMModel(**kwargs)
    if provider == "inference-client":
        return InferenceClientModel(**kwargs)

    raise ValueError(f"Unhandled model provider '{provider}'.")
