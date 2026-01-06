
import customtkinter as ctk
import threading
import sys
import os
import logging
import re
import queue
from .monitor import SystemMonitor
from .logger import logger

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TextHandler(logging.Handler):
    """
    Queue-based logger for safe GUI updates.
    """
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        msg = self.format(record)
        # Strip ANSI codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_msg = ansi_escape.sub('', msg)
        
        # Determine color tag
        tag = "INFO"
        lower_msg = msg.lower()
        if record.levelno >= logging.WARNING:
            if "usb" in lower_msg or "external drive" in lower_msg:
                tag = "USB"
            elif "clipboard" in lower_msg:
                tag = "CLIPBOARD"
            else:
                tag = "WARNING"
        elif "starting" in lower_msg or "active" in lower_msg:
            tag = "SUCCESS"
        elif "monitor" in lower_msg or "enabled" in lower_msg or "disabled" in lower_msg:
            # Capture all switch toggles (File/Clip/USB Enabled/Disabled)
            if "usb" in lower_msg:
                 tag = "USB"
            elif "clipboard" in lower_msg:
                 tag = "CLIPBOARD"
            else:
                 tag = "SUCCESS" # Green for generic/file monitor
            
        self.log_queue.put((clean_msg, tag))

class DLPApp(ctk.CTk):
    def __init__(self, monitor):
        super().__init__()

        self.monitor = monitor
        self.is_monitoring = False
        self.log_queue = queue.Queue()

        # Window Setup
        self.title("Zer0Leaks - Data Leakage Prevention")
        self.geometry(f"{1000}x{750}")

        # Main Layout (1 Column, Stacked)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) # Log area expands

        # ====================
        # 1. HEADER
        # ====================
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.header_frame.grid_columnconfigure(0, weight=1) # Spacer Left
        self.header_frame.grid_columnconfigure(1, weight=0) # Logo Center
        self.header_frame.grid_columnconfigure(2, weight=1) # Button Right

        # Logo
        self.logo_label = ctk.CTkLabel(self.header_frame, text="Zer0Leaks", font=ctk.CTkFont(size=32, weight="bold"))
        self.logo_label.grid(row=0, column=1)

        # Drawer Button (Hamburger)
        self.menu_btn = ctk.CTkButton(self.header_frame, text="☰", width=40, height=40, 
                                      command=self.toggle_drawer, font=ctk.CTkFont(size=20))
        self.menu_btn.grid(row=0, column=2, sticky="e")

        # ====================
        # 2. STATS & CONTROLS
        # ====================
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=1, column=0, sticky="ew", padx=50)
        self.controls_frame.grid_columnconfigure(0, weight=1)

        # Stats Label
        self.stats_label = ctk.CTkLabel(self.controls_frame, text=f"Monitored Directories: {len(self.monitor.watch_paths)}",
                                        font=ctk.CTkFont(size=14, weight="normal"), text_color="gray")
        self.stats_label.pack(pady=(0, 20))

        # BIG Start Button
        self.monitor_btn = ctk.CTkButton(self.controls_frame, text="START MONITORING", fg_color="#2CC985", hover_color="#229966",
                                         height=60, font=ctk.CTkFont(size=18, weight="bold"), command=self.toggle_monitoring)
        self.monitor_btn.pack(fill="x", pady=10)

        # Switches Container (Row of 3)
        self.switch_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.switch_frame.pack(pady=10)
        
        self.switch_files_var = ctk.StringVar(value="on")
        self.switch_files = ctk.CTkSwitch(self.switch_frame, text="File Monitor", variable=self.switch_files_var, 
                                          onvalue="on", offvalue="off", command=self.toggle_files_config)
        self.switch_files.select() 
        self.switch_files.pack(side="left", padx=20)

        self.usb_var = ctk.StringVar(value="off")
        self.switch_usb = ctk.CTkSwitch(self.switch_frame, text="USB Scanner", variable=self.usb_var, 
                                        onvalue="on", offvalue="off", command=self.toggle_usb)
        self.switch_usb.pack(side="left", padx=20)

        self.clip_var = ctk.StringVar(value="on")
        self.switch_clip = ctk.CTkSwitch(self.switch_frame, text="Clipboard", variable=self.clip_var, 
                                         onvalue="on", offvalue="off", command=self.toggle_clipboard_config)
        self.switch_clip.pack(side="left", padx=20)

        # ====================
        # 3. LOG CONSOLE
        # ====================
        self.console_frame = ctk.CTkFrame(self, corner_radius=10)
        self.console_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=20)
        self.console_frame.grid_rowconfigure(0, weight=1)
        self.console_frame.grid_columnconfigure(0, weight=1)

        self.log_box = ctk.CTkTextbox(self.console_frame, activate_scrollbars=True, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Colors
        self.log_box.tag_config("WARNING", foreground="#FF5555")
        self.log_box.tag_config("USB", foreground="#BD93F9")
        self.log_box.tag_config("CLIPBOARD", foreground="#F1FA8C")
        self.log_box.tag_config("SUCCESS", foreground="#50FA7B")
        self.log_box.tag_config("INFO", foreground="#F8F8F2")

        # ====================
        # 4. SLIDING DRAWER (Right Side)
        # ====================
        self.drawer_width = 250
        self.drawer_visible = False
        
        # Placed 'on top' by creating it last and using place instead of grid
        self.drawer_frame = ctk.CTkFrame(self, width=self.drawer_width, corner_radius=0, fg_color=("#dbdbdb", "#2b2b2b"))
        # Initially hidden off-screen (right)
        # Initially hidden strongly off-screen to prevent accidental overlap
        self.drawer_frame.place(relx=1.3, rely=0, relheight=1.0, anchor="ne") 

        # Drawer Content
        ctk.CTkLabel(self.drawer_frame, text="Menu", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        ctk.CTkButton(self.drawer_frame, text="Add Directory", command=self.add_dir_dialog).pack(pady=10,padx=20, fill="x")
        ctk.CTkButton(self.drawer_frame, text="Remove Directory", command=self.remove_dir_dialog).pack(pady=10,padx=20, fill="x")
        ctk.CTkButton(self.drawer_frame, text="List Directories", command=self.list_dirs_dialog).pack(pady=10,padx=20, fill="x")
        ctk.CTkButton(self.drawer_frame, text="Open Log File", command=self.open_log_file).pack(pady=10,padx=20, fill="x")
        
        ctk.CTkButton(self.drawer_frame, text="Close Menu", fg_color="gray", command=self.toggle_drawer).pack(side="bottom", pady=20)


        # Setup Internals
        text_handler = TextHandler(self.log_queue)
        logger.addHandler(text_handler)
        
        self.process_logs_loop()
        self.check_status_loop()

    # --- Drawer Animation ---
    def toggle_drawer(self):
        if self.drawer_visible:
            # Hide
            self.animate_drawer(1.3) # Move far right
            self.drawer_visible = False
        else:
            # Show
            self.drawer_frame.lift() # Ensure it's on top of everything
            self.animate_drawer(1.0) # Move to edge (visible)
            self.drawer_visible = True

    def animate_drawer(self, target_RelX):
        # A simple recursive animation function
        current_relx = float(self.drawer_frame.place_info()['relx'])
        diff = target_RelX - current_relx
        
        if abs(diff) > 0.01:
            new_relx = current_relx + (diff * 0.15) # Slightly smoother speed
            self.drawer_frame.place(relx=new_relx)
            self.after(10, lambda: self.animate_drawer(target_RelX))
        else:
            self.drawer_frame.place(relx=target_RelX)

    # --- Core Actions ---
    def toggle_monitoring(self):
        if not self.is_monitoring:
            try:
                if self.switch_files_var.get() == "on":
                    self.monitor.start_filesystem_monitor()
                
                # Clipboard check
                if self.clip_var.get() == "on":
                     self.clipboard_thread = threading.Thread(target=self.monitor.start_clipboard_monitor, daemon=True)
                     self.clipboard_thread.start()
                
                self.is_monitoring = True
                self.monitor_btn.configure(text="STOP MONITORING", fg_color="#FF5555", hover_color="#CC4444")
                if self.switch_files_var.get() == "on" or self.clip_var.get() == "on":
                    logger.info("System Monitors STARTED via GUI.")
                else:
                    logger.warning("Monitoring Started, but no modules selected.")
            except Exception as e:
                logger.error(f"Failed: {e}")
        else:
            self.monitor.stop_filesystem_monitor()
            self.monitor.running = False
            self.is_monitoring = False
            self.monitor_btn.configure(text="START MONITORING", fg_color="#2CC985", hover_color="#229966")
            logger.info("System Monitors STOPPED via GUI.")

    def toggle_usb(self):
        if self.usb_var.get() == "on":
            self.monitor.start_usb_monitor()
        else:
            self.monitor.stop_usb_monitor()
            
    def toggle_files_config(self):
        if self.is_monitoring:
            if self.switch_files_var.get() == "on":
                self.monitor.start_filesystem_monitor()
                logger.info("File Monitor Enabled.")
            else:
                self.monitor.stop_filesystem_monitor()
                logger.info("File Monitor Disabled.")

    def toggle_clipboard_config(self):
        # Clipboard monitor loop checks 'self.monitor.running'. 
        # But threading logic is tricky to stop/restart cleanly without flags. 
        # For now, we control it mainly via start button, 
        # but if we want dynamic stop, we set monitor.running = False
        if self.is_monitoring:
             if self.clip_var.get() == "off":
                 self.monitor.running = False # Stops the loop
                 logger.info("Clipboard Monitor Disabled.")
             else:
                 # Restart if it was stopped
                 if not self.monitor.running:
                     self.monitor.running = True # Reset flag
                     # Check if thread is alive, if not start new one
                     # This is a simplification; handling thread restarts robustly needs more state checks
                     self.clipboard_thread = threading.Thread(target=self.monitor.start_clipboard_monitor, daemon=True)
                     self.clipboard_thread.start()
                     logger.info("Clipboard Monitor Enabled.")

    # --- Menu Actions ---
    def add_dir_dialog(self):
        dialog = ctk.CTkInputDialog(text="Enter full path to monitor:", title="Add Directory")
        path = dialog.get_input()
        if path and os.path.exists(path):
            self.monitor.add_path(path)
            logger.info(f"Added path: {path}")
        elif path:
             logger.warning(f"Path invalid: {path}")

    def remove_dir_dialog(self):
        pass # To implement: A pop-up selector or input

    def list_dirs_dialog(self):
        paths = "\n".join(self.monitor.watch_paths)
        import tkinter.messagebox
        tkinter.messagebox.showinfo("Monitored Directories", paths)

    def open_log_file(self):
        log_path = "dlp_log.log"
        if os.path.exists(log_path):
             os.startfile(log_path) if os.name == 'nt' else None

    # --- Loops ---
    def process_logs_loop(self):
        """Batch process logs from Queue"""
        if not self.log_queue.empty():
            self.log_box.configure(state="normal")
            for _ in range(50):
                try:
                    msg, tag = self.log_queue.get_nowait()
                    self.log_box.insert("end", msg + "\n", tag)
                except queue.Empty:
                    break
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(100, self.process_logs_loop)

    def check_status_loop(self):
        # Update dynamic labels
        self.stats_label.configure(text=f"Monitored Directories: {len(self.monitor.watch_paths)}")
        
        # Sync external USB state (e.g. if logic changed it)
        if self.monitor.usb_thread_running and self.usb_var.get() == "off":
             self.switch_usb.select()
             
        self.after(1000, self.check_status_loop)
