import argparse
import sys
import os
from src.monitor import SystemMonitor
from src.logger import logger
from src.banner import show_banner
from src.cli import show_menu

def main():
    show_banner()
    parser = argparse.ArgumentParser(description="DLP Solution - Monitor & Detect")
    parser.add_argument("--path", type=str, default=".", help="Directory path to monitor (default: current dir)")
    parser.add_argument("--no-user-dirs", action="store_true", help="DISABLE monitoring of User Desktop, Documents, and Downloads")
    parser.add_argument("--external", action="store_true", help="Enable External Drive Scanner (USB)")
    args = parser.parse_args()

    # Collect paths to monitor
    paths_to_watch = []
    if args.path: paths_to_watch.append(args.path)

    # By default, we MONITOR user dirs unless explicitly disabled
    if not args.no_user_dirs:
        home = os.path.expanduser("~")
        user_dirs = [os.path.join(home, "Desktop"), os.path.join(home, "Documents"), os.path.join(home, "Downloads")]
        for d in user_dirs:
            if os.path.exists(d): paths_to_watch.append(d)
                
    paths_to_watch = list(set(paths_to_watch))

    logger.info("Starting DLP Solution...")
    logger.info(f"Monitoring directories")
    
    monitor = SystemMonitor(watch_paths=paths_to_watch)
    logger.info("System Monitors Active...")
    print("")

    # Start USB Poller if requested
    if args.external:
        monitor.start_usb_monitor()

    # Main "Run Loop"
    monitor_started = False
    
    # Show menu ONCE before starting
    # We pass clear_screen_on_start=False so the startup logs above remain visible
    show_menu(monitor, args, monitor_started=False, clear_screen_on_start=False)
    monitor_started = True

             # After returning from menu, we loop back to 'try' and restart monitors
            
    while True:
        try:
            logger.info("System Monitors Active...")
            
            # Re-announce status because previous logs were cleared by the menu
            if monitor.usb_thread_running:
                 logger.info("External Drive Scanner is Active.")
            
            logger.info(f"Monitoring directories: {monitor.watch_paths}")

            monitor.start_filesystem_monitor()
            monitor.start_clipboard_monitor() # Blocking call
        except KeyboardInterrupt:
            # When user presses Ctrl+C, pause and show menu
            monitor.stop_filesystem_monitor() 
            monitor.running = False # Stop clipboard loop
            
            show_menu(monitor, args, monitor_started=True)
            
            # After returning from menu, we loop back to 'try' and restart monitors
            logger.info("Resuming System Monitors...")
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
