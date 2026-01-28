import customtkinter as ctk
import multiprocessing
import sys
import os
import time
import ctypes
from ctypes import windll, byref, Structure, c_long, c_int, c_uint

# --- Windows API Constants & Structures for Embedding ---
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_POPUP = 0x80000000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020

class RECT(Structure):
    _fields_ = [("left", c_long), ("top", c_long), ("right", c_long), ("bottom", c_long)]

# Function to run in a separate process
def run_webview_process(url, parent_hwnd):
    import webview
    
    # Unique title to find the window later
    unique_title = f"EPIAS_EMBED_{os.getpid()}"
    
    def embed_logic():
        # Wait for the window to be created
        time.sleep(1)
        
        # 1. Find the Webview Window by Title
        # We rely on ctypes.windll.user32.FindWindowW
        hwnd = windll.user32.FindWindowW(None, unique_title)
        
        if not hwnd:
            print(f"Debug: Could not find window with title '{unique_title}'")
            return

        print(f"Debug: Found Webview HWND: {hwnd}. Reparenting to {parent_hwnd}...")

        # 2. Remove Caption and Borders to make it look embedded
        style = windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
        style = style & ~WS_CAPTION & ~WS_THICKFRAME # Remove title bar and resizing border
        style = style | WS_CHILD # Set as child window
        windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)

        # 3. Set Parent
        windll.user32.SetParent(hwnd, parent_hwnd)
        
        # 4. Resize Loop
        # Since we are in a separate process, we don't get parent resize events easily.
        # We'll poll the parent size and update the child.
        try:
            while True:
                # Get Parent Rect
                rect = RECT()
                if windll.user32.GetClientRect(parent_hwnd, byref(rect)):
                    width = rect.right - rect.left
                    height = rect.bottom - rect.top
                    
                    # Move/Resize Child to match Parent
                    windll.user32.MoveWindow(hwnd, 0, 0, width, height, True)
                
                # Check if parent still exists
                if not windll.user32.IsWindow(parent_hwnd):
                    break
                    
                time.sleep(0.1) # 10 FPS poll rate
        except Exception as e:
            print(f"Debug: Embed loop error: {e}")
        finally:
            if windll.user32.IsWindow(hwnd):
                windll.user32.PostMessageW(hwnd, 0x0010, 0, 0) # WM_CLOSE

    # Create the window (hidden initially? No, let's create normally then style it)
    webview.create_window(
        unique_title, 
        url,
        width=800, height=600,
        resizable=True
    )
    
    # Start webview with the embed logic running in a thread
    webview.start(func=embed_logic)

class WebView(ctk.CTkFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.url = "https://seffaflik.epias.com.tr/home"
        self.process = None
        
        # Grid layout
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # --- Toolbar ---
        self.toolbar = ctk.CTkFrame(self, height=40, corner_radius=0)
        self.toolbar.grid(row=0, column=0, sticky="ew")
        
        self.btn_launch = ctk.CTkButton(
            self.toolbar, 
            text="Launch EPİAŞ Portal", 
            command=self.launch_webview,
            width=150
        )
        self.btn_launch.pack(side="left", padx=10, pady=5)
        
        self.lbl_status = ctk.CTkLabel(self.toolbar, text="Status: Ready", text_color="gray")
        self.lbl_status.pack(side="left", padx=10)

        # Output Path Indicator
        self.lbl_path = ctk.CTkEntry(self.toolbar, width=400, placeholder_text="Output Path...")
        self.lbl_path.configure(state="readonly")
        self.lbl_path.pack(side="right", padx=10, pady=5)
        
        self.lbl_path_title = ctk.CTkLabel(self.toolbar, text="Save downloads to:", text_color="gray")
        self.lbl_path_title.pack(side="right", padx=5)

        # --- Placeholder Area (Where the browser will sit) ---
        self.placeholder = ctk.CTkFrame(self, corner_radius=0, fg_color="#000000")
        self.placeholder.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        
        self.info_label = ctk.CTkLabel(
            self.placeholder, 
            text="Click 'Launch' to load the portal here.",
            font=("Arial", 14),
            text_color="#888888"
        )
        self.info_label.place(relx=0.5, rely=0.5, anchor="center")

    def update_output_path(self, path):
        """Updates the path displayed in the toolbar."""
        self.lbl_path.configure(state="normal")
        self.lbl_path.delete(0, "end")
        self.lbl_path.insert(0, str(path))
        self.lbl_path.configure(state="readonly")

    def launch_webview(self):
        if self.process and self.process.is_alive():
            self.lbl_status.configure(text="Status: Browser already running", text_color="orange")
            return

        self.lbl_status.configure(text="Status: Launching...", text_color="yellow")
        
        # Ensure the frame has a valid ID by forcing an update if not yet mapped
        self.update_idletasks()
        
        # Get the window handle (HWND on Windows)
        # Note: winfo_id() returns the HWND on Windows as an integer.
        window_id = self.placeholder.winfo_id()
        print(f"Debug: Embedding WebView into Window ID: {window_id}")
        
        # Run in a separate process
        # We pass the window_id so pywebview attempts to reparent the browser window into our frame.
        self.process = multiprocessing.Process(target=run_webview_process, args=(self.url, window_id))
        self.process.start()
        
        # Monitor process
        self.after(1000, self._check_process)

    def _check_process(self):
        if self.process and self.process.is_alive():
            self.lbl_status.configure(text="Status: Running (Embedded)", text_color="green")
            # Hide the label once running
            self.info_label.place_forget()
            self.after(2000, self._check_process)
        else:
            self.lbl_status.configure(text="Status: Ready", text_color="gray")
            # Show label again if process died
            self.info_label.place(relx=0.5, rely=0.5, anchor="center")
            self.process = None
