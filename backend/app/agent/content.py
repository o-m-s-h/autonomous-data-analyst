"""Extract public answer text without exposing reasoning or provider metadata."""


def answer_text(content) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif (
            isinstance(block, dict)
            and block.get("type") == "text"
            and not block.get("thought")
            and isinstance(block.get("text"), str)
        ):
            parts.append(block["text"])
    return "\n\n".join(parts)
