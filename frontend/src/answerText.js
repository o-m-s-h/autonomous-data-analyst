// Also handle responses from backends that still return provider content blocks.
export function answerText(content) {
    if (typeof content === "string") return content;
    if (!Array.isArray(content)) return "";
    return content.flatMap((block) => {
        if (typeof block === "string") return [block];
        if (block?.type === "text" && !block.thought && typeof block.text === "string") {
            return [block.text];
        }
        return [];
    }).join("\n\n");
}
