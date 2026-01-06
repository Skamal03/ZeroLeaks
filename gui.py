
import os
import sys
import logging
from src.monitor import SystemMonitor
from src.logger import logger
from src.gui_app import DLPApp

def main():
    # Initialize Core Monitor
    # Default paths (e.g. current dir)
    paths_to_watch = ["."]
    
    # Optionally add user dirs by default, same as CLI logic
    home = os.path.expanduser("~")
    user_dirs = [os.path.join(home, "Desktop"), os.path.join(home, "Documents"), os.path.join(home, "Downloads")]
    for d in user_dirs:
        if os.path.exists(d): paths_to_watch.append(d)
                
    paths_to_watch = list(set(paths_to_watch))
    
    # logger.info("Initializing GUI...")
    
    # Disable Console Logging for GUI mode (cleaner terminal)
    # logger is a DeduplicationLogger, we need to access the underlying logger
    if hasattr(logger, 'logger'):
        real_logger = logger.logger
        for h in real_logger.handlers[:]:
            if isinstance(h, logging.StreamHandler):
                real_logger.removeHandler(h)

    monitor = SystemMonitor(watch_paths=paths_to_watch)
    
    # Launch GUI
    # The GUI app handles the event loop and interaction with the monitor
    app = DLPApp(monitor)
    app.mainloop()

if __name__ == "__main__":
    main()
