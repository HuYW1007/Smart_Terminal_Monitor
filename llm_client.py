from abc import ABC, abstractmethod
import os
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
try:
    import google.generativeai as genai
except ImportError:
    genai = None

class LLMProvider(ABC):
    @abstractmethod
    def generate_explanation(self, context: str) -> str:
        pass

    @abstractmethod
    def chat(self, messages: list) -> str:
        pass

    def _get_language_instruction(self, language: str) -> str:
        if language == 'cn':
            return "\n\n(Please answer in Chinese)"
        else:
            return "\n\n(Please answer in English)"

SYSTEM_PROMPT_EN = (
    "You are a Linux system expert specializing in resolving various Linux system issues. "
    "Analyze the provided Linux command log to determine what occurred. "
    "If the log contains alerts or errors, provide a solution after analyzing the situation."
)

SYSTEM_PROMPT_CN = (
    "你是一位 Linux 系统专家，擅长解决各种 Linux 系统问题。"
    "请分析提供的 Linux 命令日志，判断发生了什么。"
    "如果日志包含警告或错误，请在分析情况后提供解决方案。"
    "请务必使用中文回答。"
)

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: str = None, language: str = "en"):
        if OpenAI is None:
            raise ImportError("openai package is not installed. Please install it with `pip install openai`")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.language = language
        
        if language == 'cn':
            self.system_prompt = SYSTEM_PROMPT_CN
        else:
            self.system_prompt = SYSTEM_PROMPT_EN

    def generate_explanation(self, context: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Terminal output:\n{context}{self._get_language_instruction(self.language)}"}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error calling OpenAI: {e}"

    def chat(self, messages: list) -> str:
        try:
            # Append language instruction to the last user message
            messages_to_send = list(messages)
            if messages_to_send and messages_to_send[-1]["role"] == "user":
                last_msg = messages_to_send[-1].copy()
                last_msg["content"] += self._get_language_instruction(self.language)
                messages_to_send[-1] = last_msg

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_to_send
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error calling OpenAI: {e}"

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, language: str = "en"):
        if genai is None:
            raise ImportError("google-generativeai package is not installed. Please install it with `pip install google-generativeai`")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.language = language
        
        if language == 'cn':
            self.system_prompt = SYSTEM_PROMPT_CN
        else:
            self.system_prompt = SYSTEM_PROMPT_EN

    def generate_explanation(self, context: str) -> str:
        try:
            prompt = f"{self.system_prompt}\n\nTerminal output:\n{context}{self._get_language_instruction(self.language)}"
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error calling Gemini: {e}"

    def chat(self, messages: list) -> str:
        try:
            # Convert OpenAI-style messages to Gemini history
            # Note: Gemini system prompt is usually set at model init or prepended.
            # Here we will just construct a chat session or simple prompt.
            # For simplicity and statelessness in this method, we'll use a chat session with history.
            
            history = []
            last_user_message = ""
            
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                
                if role == "system":
                    # Prepend system prompt to the first user message or handle separately
                    # For now, let's just ignore it in history and assume the model knows context, 
                    # OR better, prepend it to the next user message if it's the first one.
                    # But since we initialized the model with a system prompt logic in generate_explanation,
                    # we might want to respect that.
                    # Actually, let's just use the content as is.
                    pass 
                elif role == "user":
                    history.append({"role": "user", "parts": [content]})
                    last_user_message = content
                elif role == "assistant":
                    history.append({"role": "model", "parts": [content]})
            
            # If the last message in history is the one we want to send, we should pop it?
            # No, start_chat takes history (previous messages).
            # We want to send the *last* message.
            
            if not history:
                return "Error: No messages to send."
                
            # The last message should be from user
            if history[-1]["role"] != "user":
                 return "Error: Last message must be from user."

            current_message = history.pop() # Remove last message to send it as new input
            
            # Append language instruction
            current_message_content = current_message["parts"][0]
            current_message_content += self._get_language_instruction(self.language)

            chat = self.model.start_chat(history=history)
            response = chat.send_message(current_message_content)
            return response.text
        except Exception as e:
            return f"Error calling Gemini: {e}"
