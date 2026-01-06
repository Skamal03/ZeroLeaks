
import threading
import sys
import os
from colorama import Fore, Style
from .logger import logger
from .banner import show_banner

def show_menu(monitor, args, monitor_started=False, clear_screen_on_start=True):
    """Displays the interactive menu and handles user input."""
    status_message = ""
    first_run = True

    while True:
        # Clear screen and show logo each time to create a "static" UI feel
        if first_run and not clear_screen_on_start:
             pass # Skip first clear to keep startup logs visible
             first_run = False
        else:
             show_banner(clear_screen=True)
        
        # Print Status Message if exists
        if status_message:
            print(f"{Fore.GREEN} >> {status_message} <<{Style.RESET_ALL}\n")
            status_message = "" 

        print("="*60)    
        print("             Zer0Leaks - INTERACTIVE MENU")
        print("="*60)
        print(" [1] Add Directory to Monitor")
        print(" [2] Remove Directory")
        print(" [3] List Monitored Directories")
        print(f" [4] Toggle USB Scanner (Current: {'ON' if monitor.usb_thread_running else 'OFF'})")
        print(" [5] Open Log File")
        print("")
        
        start_resume_text = "Resume Monitoring" if monitor_started else "Start Monitoring"
        print(f" [6] {start_resume_text}")
        print("")
        print(" [0] Exit")
        print("="*60)
        
        choice = input("Select an option: ").strip()
        
        if choice == '1':
            print("\n--- Add Directory ---")
            new_path = input("Enter full path to monitor: ").strip()
            if os.path.exists(new_path):
                monitor.add_path(new_path)
                status_message = f"Path added: {new_path}"
            else:
                status_message = f"Error: Path does not exist: {new_path}"
                
        elif choice == '2':
            print("\n--- Remove Directory ---")
            print("Currently Monitored:")
            for p in monitor.watch_paths:
                print(f" - {p}")
            path_to_remove = input("Enter path to remove (exact string): ").strip()
            if path_to_remove in monitor.watch_paths:
                monitor.remove_path(path_to_remove)
                status_message = f"Path removed: {path_to_remove}"
            else:
                status_message = "Path not found in list."
            
        elif choice == '3':
            print("\n--- Monitored Directories ---")
            for p in monitor.watch_paths:
                print(f" - {p}")
            input("\nPress Enter to return to menu...")
            
        elif choice == '4':
            if monitor.usb_thread_running:
                monitor.stop_usb_monitor()
                status_message = "USB Scanner Disabled."
            else:
                monitor.start_usb_monitor()
                status_message = "USB Scanner Enabled."
        
        elif choice == '5':
             log_path = "dlp_log.log"
             if os.path.exists(log_path):
                if os.name == 'nt':
                    os.startfile(log_path)
                else:
                    import subprocess
                    opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
                    subprocess.call([opener, log_path])
                status_message = "Log file opened."
             else:
                status_message = "Log file does not exist yet."

        elif choice == '6':
            os.system('cls' if os.name == 'nt' else 'clear')
            show_banner()
            action = "Resuming" if monitor_started else "Starting"
            print(f"{action}...")
            return 
            
        elif choice == '0':
            print("goodbye.")
            monitor.stop()
            sys.exit(0)
        else:
            status_message = "Invalid selection."
