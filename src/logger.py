import logging
import os
import sys
import time
import hashlib
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init(autoreset=True)

class DeduplicationLogger:
    def __init__(self, logger, cooldown_seconds=60):
        self.logger = logger
        self.cooldown = cooldown_seconds
        # Dictionary to store last logged time: {hash: timestamp}
        self.alert_history = {}

    def addHandler(self, hdlr):
        """Delegates addHandler to the underlying logger."""
        self.logger.addHandler(hdlr)

    def _generate_key(self, source, match_type, value):
        """Generates a unique key for the event."""
        # We hash the value to avoid keeping sensitive plain text in memory if possible, 
        # though the key itself is just for lookup.
        raw_str = f"{source}:{match_type}:{value}"
        return hashlib.md5(raw_str.encode()).hexdigest()

    def log_batch(self, source, matches):
        """
        Logs a batch of matches for a single source, filtering out duplicates.
        """
        new_matches = []
        now = time.time()
        
        for m in matches:
            # Create a unique key for EACH match
            key = self._generate_key(source, m['type'], m['value'])
            last_time = self.alert_history.get(key, 0)
            
            # If ANY match in this batch is new, we want to log it
            if now - last_time > self.cooldown:
                new_matches.append(m)
                self.alert_history[key] = now
        
        if new_matches:
            self.logger.warning(f"SENSITIVE DATA DETECTED in {source}!")
            for m in new_matches:
                 self.logger.warning(f"  - [{m['type']}] {m['value']} (via {m.get('method', 'Unknown')})")

    def info(self, msg):
        self.logger.info(msg)
    
    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)
        
    def exception(self, msg):
        self.logger.exception(msg)

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to warning/error logs"""
    def format(self, record):
        # Format the message formally first
        log_msg = super().format(record)
        
        # Add colors based on level
        # Custom Color Logic
        msg_lower = record.msg.lower()
        
        # 1. INFO Levels
        if record.levelno == logging.INFO:
            if "initial scan completed" in msg_lower or "performing initial scan" in msg_lower: # Green
                return Fore.GREEN + log_msg + Style.RESET_ALL
            elif "monitor started on" in msg_lower or "monitoring directories" in msg_lower or "external drive scanner" in msg_lower or "new external drive" in msg_lower: # Blue
                return Fore.BLUE + log_msg + Style.RESET_ALL
            elif "scanning file" in msg_lower: # Keep generic scanning info neutral or maybe blue? User said "scanning external drive info... blue"
                # If specific requirements for "scanning user folders info messages blue", the above covers "monitoring directories".
                pass

        # 2. WARNING Levels (Detections)
        if record.levelno == logging.WARNING:
            if "clipboard" in msg_lower: # Yellow
                return Fore.YELLOW + log_msg + Style.RESET_ALL
            elif "usb file" in msg_lower: # Purple
                return Fore.MAGENTA + log_msg + Style.RESET_ALL
            elif "file" in msg_lower: # Red (Local file default)
                return Fore.RED + log_msg + Style.RESET_ALL
            
            # Default Warning Red
            return Fore.RED + log_msg + Style.RESET_ALL
            
        # 3. ERROR/CRITICAL
        if record.levelno >= logging.ERROR:
             return Fore.RED + Style.BRIGHT + log_msg + Style.RESET_ALL
        
        return log_msg

def setup_logger(name="DLP_System", log_file="dlp_log.log", level=logging.INFO):
    """Function to setup as many loggers as you want"""
    
    # Standard formatter for file (clean text)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Colored formatter for console
    console_formatter = ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    
    # file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(file_formatter)
    
    base_logger = logging.getLogger(name)
    base_logger.setLevel(level)
    
    # Avoid adding handlers multiple times
    if not base_logger.handlers:
        base_logger.addHandler(console_handler)
        base_logger.addHandler(file_handler)
        
    return DeduplicationLogger(base_logger, cooldown_seconds=10)

# Create a default logger instance
logger = setup_logger()
