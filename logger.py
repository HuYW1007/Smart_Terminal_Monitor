import os
import datetime
import re
import glob

class ConversationLogger:
    def __init__(self, base_dir="log", log_summary_length=50):
        self.base_dir = base_dir
        self.log_summary_length = log_summary_length
        # Cache the current log file path to append to it within the same hour
        self.current_log_file = None
        self.current_log_hour = None

    def _get_log_dir(self, now):
        """Creates and returns the directory path for the given date."""
        date_str = now.strftime("%Y-%m-%d")
        log_dir = os.path.join(self.base_dir, date_str)
        os.makedirs(log_dir, exist_ok=True)
        return log_dir

    def _generate_summary(self, text):
        """Generates a short summary from the text."""
        # Remove special characters and keep only alphanumerics and spaces
        clean_text = re.sub(r'[^\w\s]', '', text).strip()
        # Collapse multiple spaces
        clean_text = re.sub(r'\s+', ' ', clean_text)
        return clean_text[:self.log_summary_length] if clean_text else "conversation"

    def _get_next_sequence(self, log_dir, hour_prefix):
        """Determines the next sequence number for the given hour."""
        # Pattern: YYYY-MM-DD_HH_SEQ_Summary.md
        # We look for files starting with the hour prefix
        pattern = os.path.join(log_dir, f"{hour_prefix}_*.md")
        files = glob.glob(pattern)
        
        max_seq = 0
        for f in files:
            basename = os.path.basename(f)
            # Expected format: YYYY-MM-DD_HH_SEQ_Summary.md
            # Split by underscore. 
            # YYYY-MM-DD_HH is 2 parts? No, YYYY-MM-DD is one part if we split by _.
            # Actually date is YYYY-MM-DD.
            # Let's parse carefully.
            # basename starts with hour_prefix (YYYY-MM-DD_HH)
            # The next part should be SEQ.
            
            try:
                # Remove prefix
                suffix = basename[len(hour_prefix)+1:] # +1 for underscore
                # suffix is SEQ_Summary.md
                parts = suffix.split('_')
                if parts:
                    seq = int(parts[0])
                    if seq > max_seq:
                        max_seq = seq
            except (ValueError, IndexError):
                continue
                
        return max_seq + 1

    def log(self, context, explanation, summary=None):
        """Logs the conversation context and explanation."""
        now = datetime.datetime.now()
        current_hour_str = now.strftime("%Y-%m-%d_%H")
        
        # Check if we need a new log file (new hour or first run)
        if self.current_log_hour != current_hour_str:
            log_dir = self._get_log_dir(now)
            
            # Determine sequence number
            seq = self._get_next_sequence(log_dir, current_hour_str)
            
            if not summary:
                summary = self._generate_summary(context)
            else:
                # Sanitize external summary just in case
                summary = self._generate_summary(summary)
            
            filename = f"{current_hour_str}_{seq:02d}_{summary}.md"
            self.current_log_file = os.path.join(log_dir, filename)
            self.current_log_hour = current_hour_str

        # Append to the log file
        try:
            with open(self.current_log_file, "a", encoding="utf-8") as f:
                f.write(f"## {now.strftime('%H:%M:%S')}\n\n")
                f.write("### Context (Input)\n")
                f.write("```\n")
                f.write(context)
                f.write("\n```\n\n")
                f.write("### Explanation (AI Response)\n")
                f.write(explanation)
                f.write("\n\n---\n\n")
        except Exception as e:
            print(f"Error writing to log file: {e}")
