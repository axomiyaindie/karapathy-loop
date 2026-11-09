import tiktoken

class ContextEngine:
    def __init__(self, token_limit: int = 4000, model_name: str = "claude-3-5-sonnet-20241022"):
        self.token_limit = token_limit
        self.history = []
        try:
            self.encoder = tiktoken.encoding_for_model("gpt-4") # Fallback layout matching target sizes
        except Exception:
            self.encoder = tiktoken.get_encoding("cl100k_base")

    def add_interaction(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    def count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def compress_context(self) -> str:
        """
        Dynamically filters historical steps, ensuring critical errors
        and recent structural changes remain within context limits.
        """
        critical_logs = []
        recent_history = []
        current_tokens = 0

        # Prioritize error payloads first
        for msg in self.history:
            if "fail" in msg["content"].lower() or "error" in msg["content"].lower():
                log_snippet = f"[{msg['role'].upper()} ERROR]: {msg['content']}\n"
                critical_logs.append(log_snippet)
                current_tokens += self.count_tokens(log_snippet)

        # Backfill with recent execution steps up to token limits
        for msg in reversed(self.history):
            formatted_msg = f"{msg['role']}: {msg['content']}\n"
            msg_tokens = self.count_tokens(formatted_msg)
            if current_tokens + msg_tokens < self.token_limit:
                recent_history.insert(0, formatted_msg)
                current_tokens += msg_tokens
            else:
                break

        summary = "--- CRITICAL HISTORY TELEMETRY ---\n" + "".join(critical_logs)
        summary += "\n--- RECENT WORKING HISTORY ---\n" + "".join(recent_history)
        return summary
