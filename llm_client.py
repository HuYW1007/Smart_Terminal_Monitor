from abc import ABC, abstractmethod
import os

class LLMProvider(ABC):
    @abstractmethod
    def generate_explanation(self, context: str) -> str:
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: str = None, language: str = "en"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.language = language
        self.system_prompt = (
            "You are an expert in programming, software installation, and Linux systems. "
            "Analyze the logs to reach a conclusion and provide a response. "
            f"Answer in {'Chinese' if language == 'cn' else 'English'}."
        )

    def generate_explanation(self, context: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Terminal output:\n{context}"}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error calling OpenAI: {e}"

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, language: str = "en"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.language = language
        self.system_prompt = (
            "You are a Linux system expert specializing in resolving various Linux system issues. "
            "Analyze the provided Linux command log to determine what occurred. "
            "If the log contains alerts or errors, provide a solution after analyzing the situation."
            f"Answer in {'Chinese' if language == 'cn' else 'English'}."
        )

    def generate_explanation(self, context: str) -> str:
        try:
            prompt = f"{self.system_prompt}\n\nTerminal output:\n{context}"
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error calling Gemini: {e}"
