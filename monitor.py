import os
import sys
import pty
import select
import tty
import termios
import fcntl
import struct
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

try:
    from .llm_client import OpenAIProvider, GeminiProvider
except ImportError:
    from llm_client import OpenAIProvider, GeminiProvider

try:
    from .logger import ConversationLogger
except ImportError:
    from logger import ConversationLogger

class TerminalMonitor:
    def __init__(self, config):
        self.config = config
        self.shell = os.environ.get('SHELL', '/bin/bash')
        self._init_llm()

    def _init_llm(self):

        
        if self.config.provider == "openai":
            self.llm = OpenAIProvider(self.config.api_key, self.config.model, self.config.base_url, self.config.language)
        elif self.config.provider == "gemini":
            self.llm = GeminiProvider(self.config.api_key, self.config.model, self.config.language)
        else:
            print(f"Warning: Unknown provider {self.config.provider}")
            self.llm = None
        

        
        log_summary_length = getattr(self.config, 'log_summary_length', 50)
        self.logger = ConversationLogger(log_summary_length=log_summary_length)

    def run(self):
        """
        Spawns the shell and monitors execution.
        """


        # First run check: Language selection
        if not self.config.language:
            print("Welcome to Smart Terminal Monitor!")
            while True:
                lang = input("Please select your preferred language (cn/en): ").strip().lower()
                if lang in ['cn', 'en']:
                    self.config.language = lang
                    self.config.save()
                    # Re-initialize LLM with new language
                    self._init_llm()
                    break
                else:
                    print("Invalid selection. Please type 'cn' or 'en'.")

        print(f"Starting smart terminal wrapper for {self.shell}...")
        print("Press Ctrl+G to ask AI for help with the last command output.")
        
        # Save original tty settings
        try:
            self.old_tty = termios.tcgetattr(sys.stdin)
        except:
            self.old_tty = None

        pid, master_fd = pty.fork()
        self.master_fd = master_fd

        if pid == 0:
            # Child process (the shell)
            os.execl(self.shell, self.shell)
        else:
            # Parent process (the monitor)
            try:
                if self.old_tty:
                    tty.setraw(sys.stdin.fileno())
                
                self._io_loop(master_fd)
                
            except Exception as e:
                print(f"\r\nMonitor error: {e}\r\n")
            finally:
                if self.old_tty:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_tty)
                os.close(master_fd)
                # Wait for child to exit
                os.waitpid(pid, 0)

    def _io_loop(self, master_fd):
        
        # Buffer for the current command output
        self.output_buffer = b""
        # Buffer for the current command input (to detect Enter)
        self.input_buffer = b""
        
        while True:
            try:
                r, w, e = select.select([sys.stdin, master_fd], [], [])
            except OSError:
                break
            
            if sys.stdin in r:
                # Read from stdin
                try:
                    d = os.read(sys.stdin.fileno(), 1024)
                    if not d:
                        break
                    
                    # Check for trigger key (Ctrl+G = \x07)
                    if b'\x07' in d:
                        self.trigger_analysis()
                        # Remove trigger key from input so shell doesn't see it
                        d = d.replace(b'\x07', b'')
                        if not d:
                            continue

                    # Check for Enter (\r or \n) to reset buffer
                    if b'\r' in d or b'\n' in d:
                        self.last_command_output = self.output_buffer
                        self.output_buffer = b""
                    
                    os.write(master_fd, d)
                except OSError:
                    break
            
            if master_fd in r:
                # Read from master_fd (shell output)
                try:
                    o = os.read(master_fd, 10240)
                    if not o:
                        break
                    
                    # Write to real stdout
                    os.write(sys.stdout.fileno(), o)
                    
                    # Buffer the output
                    self.output_buffer += o
                    
                except OSError:
                    break

    def trigger_analysis(self):
        """
        Called when user triggers the AI analysis.
        """


        output_to_analyze = self.output_buffer.decode('utf-8', errors='replace')
        if not output_to_analyze.strip():
            # If current buffer is empty, maybe they want to analyze the PREVIOUS command?
            if hasattr(self, 'last_command_output') and self.last_command_output:
                output_to_analyze = self.last_command_output.decode('utf-8', errors='replace')
        
        if not output_to_analyze.strip():
            msg = "\r\n\033[1;33m[SmartTerm] No output to analyze.\033[0m\r\n"
            os.write(sys.stdout.fileno(), msg.encode())
            return

        # Temporarily restore TTY to cooked mode for user interaction
        current_tty = None
        try:
            current_tty = termios.tcgetattr(sys.stdin)
            if self.old_tty:
                # Create a copy of old_tty settings
                new_settings = list(self.old_tty)
                # Disable ECHOCTL to prevent ^C from being echoed by terminal
                new_settings[3] = new_settings[3] & ~termios.ECHOCTL
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, new_settings)
        except:
            pass

        # Truncate output if it exceeds max_context_chars
        max_chars = getattr(self.config, 'max_context_chars', 10000)
        if len(output_to_analyze) > max_chars:
            output_to_analyze = output_to_analyze[-max_chars:]
            msg = f"\r\n\033[1;33m[SmartTerm] Output truncated to last {max_chars} chars.\033[0m"
            os.write(sys.stdout.fileno(), msg.encode())

        msg = f"\r\n\033[1;34m[SmartTerm] Analyzing {len(output_to_analyze)} chars...\033[0m\r\n"
        os.write(sys.stdout.fileno(), msg.encode())
        
        # Flag to track if we exited via Ctrl+C
        interrupted = False

        if self.llm:
            # Initialize chat messages
            messages = [
                {"role": "system", "content": self.llm.system_prompt},
                {"role": "user", "content": f"Terminal output:\n{output_to_analyze}"}
            ]

            console = Console(force_terminal=True, width=80)

            while True:
                try:
                    # Get response from LLM
                    if hasattr(self.llm, 'chat'):
                        explanation = self.llm.chat(messages)
                    else:
                        # Fallback for providers without chat
                        explanation = self.llm.generate_explanation(output_to_analyze)

                    # Display response
                    print() # Newline
                    console.print(Panel(Markdown(explanation), title="SmartTerm AI Suggestion", border_style="green"))
                    print() # Newline

                    # Generate summary for log filename
                    log_summary_length = getattr(self.config, 'log_summary_length', 50)
                    generated_summary = None
                    try:
                        summary_prompt = [
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": f"Summarize the following terminal output in one sentence (max {log_summary_length} chars) for a filename. Do not use special characters. Output:\n{output_to_analyze}"}
                        ]
                        if hasattr(self.llm, 'chat'):
                            # We use a separate chat call, but we don't want to mess up the main conversation history if possible.
                            # Actually, self.llm.chat takes messages. We can just call it.
                            # But wait, self.llm.chat might modify internal state for Gemini?
                            # GeminiProvider.chat uses history but doesn't store it in the object (it creates a new chat session each time).
                            # So it's safe.
                            generated_summary = self.llm.chat(summary_prompt)
                        else:
                            # Fallback
                            generated_summary = self.llm.generate_explanation(f"Summarize this for a filename (max {log_summary_length} chars): {output_to_analyze}")
                        
                        # Clean up summary
                        if generated_summary:
                            generated_summary = generated_summary.strip().replace('\n', ' ').replace('\r', '')
                    except Exception as e:
                        print(f"Error generating summary: {e}")

                    # Log the interaction
                    log_context = messages[-1]["content"]
                    self.logger.log(log_context, explanation, summary=generated_summary)

                    # Append assistant response to history
                    messages.append({"role": "assistant", "content": explanation})

                    # Prompt for user input
                    try:
                        user_input = input("\033[1;33mUser (Ctrl+C to exit): \033[0m")
                        if not user_input.strip():
                            continue
                        
                        # Append user input to history
                        messages.append({"role": "user", "content": user_input})
                        
                    except KeyboardInterrupt:
                        # Just break the loop cleanly
                        interrupted = True
                        break
                    except EOFError:
                        break

                except KeyboardInterrupt:
                    # Handle Ctrl+C during LLM generation
                    interrupted = True
                    break
                except Exception as e:
                    print(f"\n\033[1;31mError: {e}\033[0m")
                    break
            
        else:
            msg = "\r\n\033[1;31m[SmartTerm] No LLM provider configured.\033[0m\r\n"
            os.write(sys.stdout.fileno(), msg.encode())

        # Restore TTY to raw mode (or whatever it was before)
        if current_tty:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, current_tty)
            except:
                pass

        # If interrupted by user, send SIGINT to shell to print ^C and show prompt immediately
        if interrupted:
            os.write(self.master_fd, b'\x03')




