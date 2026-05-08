import ast
import json
import re
from typing import Any, Optional

import litellm
from litellm import completion, completion_cost
from litellm.caching.caching import Cache
from litellm.main import ModelResponse, Usage
from loguru import logger

from kc.config import (
    DEFAULT_LLM_CACHE_TYPE,
    DEFAULT_MAX_RETRIES,
    LLM_CACHE_ENABLED,
    REDIS_CACHE_TTL,
    REDIS_CACHE_VERSION,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
    REDIS_PREFIX,
    USE_LANGFUSE,
)
from kc.data_model.message import (
    AssistantMessage,
    Message,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from kc.environment.tool import Tool

# litellm._turn_on_debug()

if USE_LANGFUSE:
    # set callbacks
    litellm.success_callback = ["langfuse"]
    litellm.failure_callback = ["langfuse"]

litellm.drop_params = True

if LLM_CACHE_ENABLED:
    if DEFAULT_LLM_CACHE_TYPE == "redis":
        logger.info(f"LiteLLM: Using Redis cache at {REDIS_HOST}:{REDIS_PORT}")
        litellm.cache = Cache(
            type=DEFAULT_LLM_CACHE_TYPE,
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            namespace=f"{REDIS_PREFIX}:{REDIS_CACHE_VERSION}:litellm",
            ttl=REDIS_CACHE_TTL,
        )
    elif DEFAULT_LLM_CACHE_TYPE == "local":
        logger.info("LiteLLM: Using local cache")
        litellm.cache = Cache(
            type="local",
            ttl=REDIS_CACHE_TTL,
        )
    else:
        raise ValueError(
            f"Invalid cache type: {DEFAULT_LLM_CACHE_TYPE}. Should be 'redis' or 'local'"
        )
    litellm.enable_cache()
else:
    logger.info("LiteLLM: Cache is disabled")
    litellm.disable_cache()


ALLOW_SONNET_THINKING = False

if not ALLOW_SONNET_THINKING:
    logger.warning("Sonnet thinking is disabled")


def _parse_ft_model_name(model: str) -> str:
    """
    Parse the ft model name from the litellm model name.
    e.g: "ft:gpt-4.1-mini-2025-04-14:sierra::BSQA2TFg" -> "gpt-4.1-mini-2025-04-14"
    """
    pattern = r"ft:(?P<model>[^:]+):(?P<provider>\w+)::(?P<id>\w+)"
    match = re.match(pattern, model)
    if match:
        return match.group("model")
    else:
        return model


def get_response_cost(response: ModelResponse) -> float:
    """
    Get the cost of the response from the litellm completion.
    """
    response.model = _parse_ft_model_name(
        response.model
    )  # FIXME: Check Litellm, passing the model to completion_cost doesn't work.
    try:
        cost = completion_cost(completion_response=response)
    except Exception as e:
        logger.error(e)
        return 0.0
    return cost


def get_response_usage(response: ModelResponse) -> Optional[dict]:
    usage: Optional[Usage] = response.get("usage")
    if usage is None:
        return None
    return {
        "completion_tokens": usage.completion_tokens,
        "prompt_tokens": usage.prompt_tokens,
    }


def to_tau2_messages(
    messages: list[dict], ignore_roles: set[str] = set()
) -> list[Message]:
    """
    Convert a list of messages from a dictionary to a list of Tau2 messages.
    """
    tau2_messages = []
    for message in messages:
        role = message["role"]
        if role in ignore_roles:
            continue
        if role == "user":
            tau2_messages.append(UserMessage(**message))
        elif role == "assistant":
            tau2_messages.append(AssistantMessage(**message))
        elif role == "tool":
            tau2_messages.append(ToolMessage(**message))
        elif role == "system":
            tau2_messages.append(SystemMessage(**message))
        else:
            raise ValueError(f"Unknown message type: {role}")
    return tau2_messages


def to_litellm_messages(messages: list[Message]) -> list[dict]:
    """
    Convert a list of Tau2 messages to a list of litellm messages.
    """
    litellm_messages = []
    for message in messages:
        if isinstance(message, UserMessage):
            litellm_messages.append({"role": "user", "content": message.content})
        elif isinstance(message, AssistantMessage):
            tool_calls = None
            if message.is_tool_call():
                tool_calls = [
                    {
                        "id": tc.id,
                        "name": tc.name,
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                        "type": "function",
                    }
                    for tc in message.tool_calls
                ]
            litellm_messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": tool_calls,
                }
            )
        elif isinstance(message, ToolMessage):
            litellm_messages.append(
                {
                    "role": "tool",
                    "content": message.content,
                    "tool_call_id": message.id,
                }
            )
        elif isinstance(message, SystemMessage):
            litellm_messages.append({"role": "system", "content": message.content})
    return litellm_messages


def generate(
    model: str,
    messages: list[Message],
    tools: Optional[list[Tool]] = None,
    tool_choice: Optional[str] = None,
    **kwargs: Any,
) -> UserMessage | AssistantMessage:
    """
    Generate a response from the model.

    Args:
        model: The model to use.
        messages: The messages to send to the model.
        tools: The tools to use.
        tool_choice: The tool choice to use.
        **kwargs: Additional arguments to pass to the model.

    Returns: A tuple containing the message and the cost.
    """
    if kwargs.get("num_retries") is None:
        kwargs["num_retries"] = DEFAULT_MAX_RETRIES

    if model.startswith("claude") and not ALLOW_SONNET_THINKING:
        kwargs["thinking"] = {"type": "disabled"}
    litellm_messages = to_litellm_messages(messages)
    tools = [tool.openai_schema for tool in tools] if tools else None
    if tools and tool_choice is None:
        tool_choice = "auto"
    try:
        response = completion(
            model=model,
            messages=litellm_messages,
            tools=tools,
            tool_choice=tool_choice,
            timeout=3600,
            **kwargs,
        )
    except Exception as e:
        logger.error(e)
        raise e
    cost = get_response_cost(response)
    usage = get_response_usage(response)
    response = response.choices[0]
    try:
        finish_reason = response.finish_reason
        if finish_reason == "length":
            logger.warning("Output might be incomplete due to token limit!")
    except Exception as e:
        logger.error(e)
        raise e
    assert response.message.role == "assistant", (
        "The response should be an assistant message"
    )
    import uuid
    content = response.message.content or ""
    raw_tool_calls = getattr(response.message, "tool_calls", None) or []
    parsed_tool_calls = []

    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    if "</think>" in content:
        content = re.sub(r".*?</think>", "", content, flags=re.DOTALL)
    content = re.sub(r"<think>.*$", "", content, flags=re.DOTALL).strip()

    def _parse_val(v):
        if isinstance(v, (dict, list)): return v
        if not v: return {}
        try: return json.loads(v)
        except: 
            try: return ast.literal_eval(v)
            except: return v

    for tc in raw_tool_calls:
        try:
            func = getattr(tc, "function", tc)
            func_name = getattr(func, "name", None)
            func_args = getattr(func, "arguments", "{}")
            tc_id = getattr(tc, "id", f"call_{uuid.uuid4().hex[:8]}")
            
            if func_name:
                args = _parse_val(func_args)
                parsed_tool_calls.append(ToolCall(
                    id=tc_id, 
                    name=func_name, 
                    arguments=args if isinstance(args, dict) else {}
                ))
        except Exception as e:
            logger.warning(f"Failed to parse standard tool arguments: {e}")


    if not raw_tool_calls:
            content = re.sub(r"\*\*Tool Call:\*\*", "", content)
            combined_pattern = (
                r"(?:<tool_call>|<\|python_tag\|>|<\|python_start\|>)"
                r"(.*?)"
                r"(?:</tool_call>|<\|python_end\|>|(?=<tool_call>)|(?=<\|python_tag\|>)|(?=<\|python_start\|>)|$)"
            )
            matches = list(re.finditer(combined_pattern, content, re.DOTALL))
            for match in reversed(matches):
                block = match.group(1)
                full_match_text = match.group(0) 
                try:
                    json_match = re.search(r"\{.*\}", block, re.DOTALL)
                    if json_match:
                        obj = json.loads(json_match.group())
                        name = None
                        args = None
                        if isinstance(obj, dict):
                            name = obj.get("action") or obj.get("name") or obj.get("tool")
                            args = obj.get("parameters") or obj.get("arguments") or obj.get("content")
                            if obj.get("type") == "function" and not name:
                                name = obj.get("name")
                                args = obj.get("parameters") or obj.get("arguments")

                        if name:
                            parsed_tool_calls.append(ToolCall(
                                id=f"call_{uuid.uuid4().hex[:8]}",
                                name=name,
                                arguments=_parse_val(args) if args is not None else {}
                            ))
                     
                            content = content[:match.start()] + content[match.end():]
                except Exception as e:
                    logger.debug(f"Failed to parse tag block: {e}")

           
            decoder = json.JSONDecoder()
            cursor = 0
            while cursor < len(content):
                start_idx = content.find('{', cursor)
                if start_idx == -1: 
                    break
                try:
                    obj, end_pos = decoder.raw_decode(content[start_idx:])
                    
                    is_valid_tool = False
                    name = None
                    args = None

                    if isinstance(obj, dict) and "function" in obj and isinstance(obj["function"], dict):
                        name = obj["function"].get("name")
                        args = obj["function"].get("arguments")
                        is_valid_tool = True
                    
                    elif isinstance(obj, dict) and "name" in obj and ("arguments" in obj or "parameters" in obj):
                        name = obj.get("name")
                        args = obj.get("arguments") or obj.get("parameters")
                        is_valid_tool = True

                    elif (
                        isinstance(obj, dict)
                        and obj.get("type") == "function"
                        and "name" in obj
                        and "parameters" in obj
                    ):
                        name = obj.get("name")
                        args = obj.get("parameters")
                        is_valid_tool = True

                    elif (
                        isinstance(obj, dict)
                        and obj.get("type") == "function"
                        and "name" in obj
                        and "arguments" in obj
                    ):
                        name = obj.get("name")
                        args = obj.get("arguments")
                        is_valid_tool = True
                        
                    elif isinstance(obj, dict) and "action" in obj:
                        name = obj.get("action")
                        args = obj.get("parameters") or obj.get("content")
                        is_valid_tool = True

                    if is_valid_tool and isinstance(name, str) and name != "think":
                        final_args = _parse_val(args)
                        if not isinstance(final_args, dict) and final_args is not None:
                            final_args = {"content": final_args}
                            
                        parsed_tool_calls.append(ToolCall(
                            id=f"call_{uuid.uuid4().hex[:8]}", 
                            name=name, 
                            arguments=final_args if final_args is not None else {}
                        ))
                        content = content[:start_idx] + content[start_idx + end_pos:]
                        cursor = start_idx 
                        continue 
                    
                    cursor = start_idx + end_pos
                except json.JSONDecodeError:
                    cursor = start_idx + 1
                except Exception as e:
                    logger.debug(f"JSON scan skip: {e}")
                    cursor = start_idx + 1


            xml_func_pattern = r"<function=(?P<name>[^>]+)>(?P<body>.*?)</function>"
            xml_param_pattern = r"<parameter=(?P<key>[^>]+)>(?P<val>.*?)</parameter>"
            
            for func_match in re.finditer(xml_func_pattern, content, re.DOTALL):
                f_name = func_match.group("name").strip()
                f_body = func_match.group("body")
                
                args = {}
                for p_match in re.finditer(xml_param_pattern, f_body, re.DOTALL):
                    p_key = p_match.group("key").strip()
                    p_val = p_match.group("val").strip()
                    args[p_key] = _parse_val(p_val) 
                    
                if f_name:
                    parsed_tool_calls.append(ToolCall(
                        id=f"call_{uuid.uuid4().hex[:8]}",
                        name=f_name,
                        arguments=args
                    ))
                    content = content.replace(func_match.group(0), "")

    content = re.sub(
    r"<(?:tool_call|/tool_call|\|python_tag\||\|python_start\||\|python_end\||/?function(?:=[^>]+)?|/?parameter(?:=[^>]+)?)>",
    "",
    content,
)    
    content = content.strip()
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    if len(lines) > 2 and lines[:len(lines)//2] == lines[len(lines)//2:]:
        content = "\n".join(lines[:len(lines)//2])

    tool_calls = parsed_tool_calls if parsed_tool_calls else None
    
    if not content and not tool_calls:
        raw_preview = ""
        try:
            raw_preview = (getattr(response.message, "content", "") or "")[:300]
        except Exception:
            pass
        logger.warning(
            "Model returned an empty assistant message (no content, no tool_calls). Injecting fallback text. "
            f"raw_preview={raw_preview!r}"
        )
        content = "I'm sorry, I couldn't generate a valid response just now. Please try again."

    if isinstance(content, str):
        content = content.strip()
        if content == "":
            content = None

    message = AssistantMessage(
        role="assistant",
        content=content,
        tool_calls=tool_calls,
        cost=cost,
        usage=usage,
        raw_data=response.to_dict() if hasattr(response, "to_dict") else {},
    )
    return message


def get_cost(messages: list[Message]) -> tuple[float, float] | None:
    """
    Get the cost of the interaction between the agent and the user.
    Returns None if any message has no cost.
    """
    agent_cost = 0
    user_cost = 0
    for message in messages:
        if isinstance(message, ToolMessage):
            continue
        if message.cost is not None:
            if isinstance(message, AssistantMessage):
                agent_cost += message.cost
            elif isinstance(message, UserMessage):
                user_cost += message.cost
        else:
            logger.warning(f"Message {message.role}: {message.content} has no cost")
            return None
    return agent_cost, user_cost


def get_token_usage(messages: list[Message]) -> dict:
    """
    Get the token usage of the interaction between the agent and the user.
    """
    usage = {"completion_tokens": 0, "prompt_tokens": 0}
    for message in messages:
        if isinstance(message, ToolMessage):
            continue
        if message.usage is None:
            logger.warning(f"Message {message.role}: {message.content} has no usage")
            continue
        usage["completion_tokens"] += message.usage["completion_tokens"]
        usage["prompt_tokens"] += message.usage["prompt_tokens"]
    return usage
