# Smart Terminal Monitor / 智能终端监控助手

## Overview / 简介
The Smart Terminal Monitor is a Python application that wraps your shell session. It monitors the output of your commands and allows you to ask an AI for help when something goes wrong, without needing to copy-paste logs.

智能终端监控助手是一个 Python 应用程序，它包裹了您的 Shell 会话。它监控命令输出，当出现问题时，您可以一键请求 AI 帮助，无需手动复制粘贴日志。

## Features / 功能特性
- **Transparent Shell Wrapper**: Runs your default shell (bash, zsh, etc.) inside a PTY.
  **透明 Shell 包装**: 在 PTY 中运行您的默认 Shell（bash, zsh 等）。
- **AI Integration**: Supports OpenAI, Gemini, and other OpenAI-compatible providers (e.g., DeepSeek).
  **AI 集成**: 支持 OpenAI, Gemini 以及其他兼容 OpenAI 接口的模型（如 DeepSeek）。
- **One-Key Analysis**: Press `Ctrl+G` to analyze the output of the last command.
  **一键分析**: 按下 `Ctrl+G` 即可分析上一条命令的输出。
- **Rich Output**: AI suggestions are rendered in Markdown directly in your terminal.
  **富文本输出**: AI 建议直接在终端中以 Markdown 格式渲染。
- **Bilingual Support**: Supports English and Chinese responses, configurable via settings.
  **双语支持**: 支持中英文回答，可通过配置进行修改。
- **Expert Persona**: AI acts as a Linux and programming expert to provide precise solutions.
  **专家人设**: AI 扮演 Linux 和编程专家，提供精准的解决方案。

## Setup / 安装与配置

1.  **Install Dependencies / 安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configuration / 配置**:
    Create a file `smart_term_config.yaml` in the project directory or `~/.smart_term_config.yaml` with your API keys:
    
    在项目目录或 `~/.smart_term_config.yaml` 创建配置文件 `smart_term_config.yaml`，填入您的 API Key：

    ```yaml
    provider: openai  # or gemini
    api_key: sk-...
    model: gpt-4o     # or gemini-pro, deepseek-chat
    base_url: ...     # optional, for other providers (e.g., https://api.deepseek.com)
    language: cn      # optional, 'cn' or 'en' (auto-detected on first run / 首次运行自动检测)
    ```
    
    Alternatively, set environment variables / 或者设置环境变量:
    ```bash
    export SMART_TERM_API_KEY="your-key"
    export SMART_TERM_BASE_URL="your-url"
    ```

## Usage / 使用指南

1.  **Start the Monitor / 启动监控**:
    ```bash
    python3 main.py
    ```
    *On first run, you will be asked to select your preferred language.*
    
    *首次运行时，会提示您选择偏好语言。*

2.  **Run Commands / 运行命令**:
    Use your terminal as usual.
    
    像往常一样使用终端。
    ```bash
    $ ls -z
    ls: invalid option -- 'z'
    Try 'ls --help' for more information.
    ```

3.  **Ask for Help / 请求帮助**:
    Press `Ctrl+G`. The AI will analyze the error and suggest a fix.
    
    按下 `Ctrl+G`。AI 将分析错误并给出修复建议。

    > [!TIP]
    > The monitor buffers output per command (resetting on Enter). If you want to analyze a long running command's output, just press `Ctrl+G` after it finishes.
    > 
    > 监控器按命令缓冲输出（回车重置）。如果要分析长运行命令的输出，请在命令结束后按下 `Ctrl+G`。
