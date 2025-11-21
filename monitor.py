import os
import sys

class TerminalMonitor:
    def __init__(self, config):
        self.config = config
        self.shell = os.environ.get('SHELL', '/bin/bash')
        self._init_llm()

    def _init_llm(self):
        try:
            from .llm_client import OpenAIProvider, GeminiProvider
        except ImportError:
            from llm_client import OpenAIProvider, GeminiProvider
        
        if self.config.provider == "openai":
            self.llm = OpenAIProvider(self.config.api_key, self.config.model, self.config.base_url, self.config.language)
        elif self.config.provider == "gemini":
            self.llm = GeminiProvider(self.config.api_key, self.config.model, self.config.language)
        else:
            print(f"Warning: Unknown provider {self.config.provider}")
            self.llm = None

    def run(self):
        """
        Spawns the shell and monitors execution.
        """
        import pty
        import select
        import tty
        import termios
        import fcntl
        import struct

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
            old_tty = termios.tcgetattr(sys.stdin)
        except:
            old_tty = None

        pid, master_fd = pty.fork()

        if pid == 0:
            # Child process (the shell)
            os.execl(self.shell, self.shell)
        else:
            # Parent process (the monitor)
            try:
                if old_tty:
                    tty.setraw(sys.stdin.fileno())
                
                self._io_loop(master_fd)
                
            except Exception as e:
                print(f"\r\nMonitor error: {e}\r\n")
            finally:
                if old_tty:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
                os.close(master_fd)
                # Wait for child to exit
                os.waitpid(pid, 0)

    def _io_loop(self, master_fd):
        import select
        
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
        import termios
        import tty
        from rich.console import Console
        from rich.markdown import Markdown
        from rich.panel import Panel

        output_to_analyze = self.output_buffer.decode('utf-8', errors='replace')
        if not output_to_analyze.strip():
            # If current buffer is empty, maybe they want to analyze the PREVIOUS command?
            if hasattr(self, 'last_command_output') and self.last_command_output:
                output_to_analyze = self.last_command_output.decode('utf-8', errors='replace')
        
        if not output_to_analyze.strip():
            msg = "\r\n\033[1;33m[SmartTerm] No output to analyze.\033[0m\r\n"
            os.write(sys.stdout.fileno(), msg.encode())
            return

        # Temporarily restore TTY to cooked mode for Rich printing
        try:
            current_tty = termios.tcgetattr(sys.stdin)
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, termios.tcgetattr(sys.stdout)) # Reset to stdout settings? Or just cooked?
            # Actually, we should have saved the 'original' settings in __init__ or run
            # But we can just use a simpler approach: print \r\n manually with Rich?
            # Rich console has a 'force_terminal' option.
            # But if we are in RAW mode, newlines are just \n, we need \r\n.
            # It's safer to temporarily restore the original TTY settings we saved in run().
            # However, 'run' local variable 'old_tty' is not accessible here.
            # Let's store old_tty in self.
        except:
            pass

        # We need to access old_tty. Let's modify run() to store it in self.old_tty
        # For now, assuming we are in raw mode, we can try to use Rich but it might look weird if we don't handle \r.
        
        msg = f"\r\n\033[1;34m[SmartTerm] Analyzing {len(output_to_analyze)} chars...\033[0m\r\n"
        os.write(sys.stdout.fileno(), msg.encode())
        
        if self.llm:
            explanation = self.llm.generate_explanation(output_to_analyze)
            
            # Use Rich to render Markdown
            # We need to write to a string buffer first to handle line endings if we stay in raw mode
            # OR we can just temporarily switch to cooked mode if we have the settings.
            
            # Let's try a hybrid approach: Use Rich to render to string, then replace \n with \r\n
            console = Console(force_terminal=True, width=80) # Fixed width for safety
            with console.capture() as capture:
                console.print(Panel(Markdown(explanation), title="SmartTerm AI Suggestion", border_style="green"))
            
            rendered_output = capture.get()
            rendered_output = rendered_output.replace('\n', '\r\n')
            
            os.write(sys.stdout.fileno(), f"\r\n{rendered_output}\r\n".encode())
            
        else:
            msg = "\r\n\033[1;31m[SmartTerm] No LLM provider configured.\033[0m\r\n"
            os.write(sys.stdout.fileno(), msg.encode())

