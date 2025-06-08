class LLMInterface:
    def send_prompt(self, prompt: str) -> str:
        raise NotImplementedError
