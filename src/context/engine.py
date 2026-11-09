class ContextEngine:
    def __init__(self, token_limit: int = 4000):
        self.token_limit = token_limit
        self.history = []
    def add_interaction(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
    def compress_context(self) -> str:
        return f"Aggregated history logs: {len(self.history)} steps recorded."
