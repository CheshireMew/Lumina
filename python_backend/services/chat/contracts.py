CHAT_HOOKS = {
    "input_preprocess": "chat.input_preprocess",
    "context_build": "chat.context_build",
    "tool_resolve": "chat.tool_resolve",
    "generate": "chat.generate",
    "output_filter": "chat.output_filter",
    "post_turn": "chat.post_turn",
}


def list_chat_hook_specs() -> list[dict[str, str]]:
    return [
        {"slot": slot, "hook": hook}
        for slot, hook in CHAT_HOOKS.items()
    ]
