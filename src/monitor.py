import time
import os
import threading
import pyperclip
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .logger import logger
from .detector import PII_Detector
from .usb_detector import get_removable_drives

class FileEventHandler(FileSystemEventHandler):
    def __init__(self, detector):
        self.detector = detector

    def on_created(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)

    def process_file(self, file_path):
        """Reads file content and scans for PII"""
        try:
            # Simple text file check for now
            if not self.should_scan(file_path):
                return
            
            logger.info(f"Scanning file: {file_path}")

            # Brief sleep to ensure file write is complete (prevents empty reads on some editors)
            time.sleep(0.5)

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            matches = self.detector.scan_text(content)
            if matches:
                 # Check if file is on a removable drive
                 is_usb = False
                 try:
                     removable_drives = get_removable_drives()
                     for drive in removable_drives:
                         if file_path.lower().startswith(drive.lower()):
                             is_usb = True
                             break
                 except:
                     pass

                 source_label = f"USB file {file_path}" if is_usb else f"file {file_path}"
                 logger.log_batch(source=source_label, matches=matches)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")

    def should_scan(self, file_path):
        """Decides if a file should be scanned."""
        filename = os.path.basename(file_path)
        
        # 1. Ignore specific system/project files
        ignored_files = {
            'dlp_log.log', 'requirements.txt', 'task.md', 'implementation_plan.md', 
            'walkthrough.md', 'verify_setup.py', 'monitor.py', 'detector.py', 
            'logger.py', 'main.py'
        }
        if filename in ignored_files:
            return False

        # 2. Ignore specific directories
        # Check if any part of the path is in ignored list
        parts = file_path.split(os.sep)
        ignored_dirs = {'.git', '.vscode', '__pycache__', '.venv', 'env', 'src', '.gemini', 'docs'}
        if any(p in ignored_dirs for p in parts):
            return False

        # 3. Inclusion Rules (Only scan specific text formats)
        valid_extensions = ('.txt', '.csv', '.log', '.md', '.json', '.xml')
        if not file_path.endswith(valid_extensions):
            return False
            
        return True

class SystemMonitor:
    def __init__(self, watch_paths=None):
        self.detector = PII_Detector()
        # Ensure watch_paths is a list. Default to current directory if None.
        if watch_paths is None:
            watch_paths = ["."]
        elif isinstance(watch_paths, str):
            watch_paths = [watch_paths]
            
        self.watch_paths = watch_paths
        self.observer = Observer()
        self.running = False
        self.usb_thread = None
        self.usb_thread_running = False
        self.known_drives = set()

    def scan_existing_files(self, specific_path=None):
        """Scans all existing files in the watch paths (or a specific one) on startup."""
        paths_to_scan = [specific_path] if specific_path else self.watch_paths
        
        for path in paths_to_scan:
            logger.info(f"Performing initial scan of: {os.path.abspath(path)}")
            event_handler = FileEventHandler(self.detector)
            # Walk through each watched path
            if os.path.exists(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        event_handler.process_file(file_path)
            else:
                logger.warning(f"Path not found: {path}")
        
        if not specific_path:
            logger.info("Initial scan completed.")

    def add_path(self, path):
        """Dynamically adds a new path to the monitor."""
        if path in self.watch_paths:
            return
            
        if not os.path.isdir(path):
            logger.warning(f"Cannot add path, not a directory: {path}")
            return

        logger.info(f"Adding new monitoring path: {path}")
        self.watch_paths.append(path)
        
        # Schedule the observer
        event_handler = FileEventHandler(self.detector)
        self.observer.schedule(event_handler, path, recursive=True)
        
        # Perform initial scan for this new path
        self.scan_existing_files(specific_path=path)

    def remove_path(self, path):
        """Stops monitoring a specific path."""
        path = os.path.abspath(path)
        if path not in self.watch_paths:
            logger.warning(f"Path not found in monitor list: {path}")
            return

        logger.info(f"Removing monitoring path: {path}")
        self.watch_paths.remove(path)
        
        # Watchdog doesn't easily support removing one watch. 
        # We have to restart the observer with the remaining paths.
        self.stop_filesystem_monitor()
        self.start_filesystem_monitor()

    def start_filesystem_monitor(self):
        if self.observer.is_alive():
             # Already running
             return

        # Re-create observer in case it was stopped
        self.observer = Observer()
        event_handler = FileEventHandler(self.detector)
        
        assigned_watch = False
        for path in self.watch_paths:
            if os.path.isdir(path):
                self.observer.schedule(event_handler, path, recursive=True)
                logger.info(f"File system monitor started on: {os.path.abspath(path)}")
                assigned_watch = True
            else:
                logger.warning(f"Directory not found, skipping: {path}")
        
        if assigned_watch:
            self.observer.start()

    def stop_filesystem_monitor(self):
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()

    def start_clipboard_monitor(self, interval=1.0):
        logger.info("Clipboard monitor started.")
        
        # Perform initial file scan now that everything is started
        self.scan_existing_files()

        self.running = True
        last_content = ""
        
        try:
            while self.running:
                content = pyperclip.paste()
                if content != last_content:
                    last_content = content
                    if content.strip():
                        # Scan new clipboard content
                        matches = self.detector.scan_text(content)
                        if matches:
                            logger.log_batch(source="Clipboard", matches=matches)
                                
                            # Optional: Clear clipboard if sensitive?
                            # pyperclip.copy("") 
                            
                time.sleep(interval)
        except KeyboardInterrupt:
             # Allow KeyboardInterrupt to propagate up to main menu
             raise
        except Exception as e:
            logger.error(f"Clipboard Error: {e}")

    def start_all(self):
        self.start_filesystem_monitor()
        self.start_clipboard_monitor()

    def start_usb_monitor(self, interval=5):
        """Starts the background USB polling thread."""
        if self.usb_thread_running:
            return

        logger.info("External Drive Scanner started. Waiting for USB...")
        self.usb_thread_running = True
        
        # Initialize known drives
        current_drives = get_removable_drives()
        for d in current_drives:
            self.known_drives.add(d)
            self.add_path(d)

        self.usb_thread = threading.Thread(target=self._poll_usb_drives, args=(interval,), daemon=True)
        self.usb_thread.start()

    def stop_usb_monitor(self):
        """Stops the USB polling thread."""
        if self.usb_thread_running:
            self.usb_thread_running = False
            if self.usb_thread:
                self.usb_thread.join(timeout=1.0)
            logger.info("External Drive Scanner stopped.")

    def _poll_usb_drives(self, interval):
        while self.usb_thread_running:
            try:
                current_drives = get_removable_drives()
                for drive in current_drives:
                    if drive not in self.known_drives:
                        logger.info(f"New external drive detected: {drive}")
                        self.add_path(drive) 
                        self.known_drives.add(drive)
                time.sleep(interval)
            except Exception as e:
                logger.error(f"USB Polling Error: {e}")
                time.sleep(interval)

    def stop(self):
        self.running = False
        self.stop_filesystem_monitor()
        self.stop_usb_monitor()
        logger.info("Monitors stopped.")
