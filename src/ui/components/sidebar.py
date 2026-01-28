import customtkinter as ctk
import tkinter as tk

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, 
                 on_file_select_callback=None, 
                 on_open_file_callback=None, 
                 on_delete_file_callback=None, 
                 on_ptf_change_callback=None,
                 on_add_ptf_callback=None,
                 on_view_ptf_callback=None,
                 **kwargs):
        super().__init__(master, **kwargs)
        self.on_file_select_callback = on_file_select_callback
        self.on_open_file_callback = on_open_file_callback
        self.on_delete_file_callback = on_delete_file_callback
        self.on_ptf_change_callback = on_ptf_change_callback
        self.on_add_ptf_callback = on_add_ptf_callback
        self.on_view_ptf_callback = on_view_ptf_callback
        
        self.buttons = []
        self.current_files = [] 
        self.ptf_files = [] # List of available PTF files

        # Grid layout
        # Row 0: PTF Section (Header)
        # Row 1: PTF Dropdown
        # Row 2: File List Header
        # Row 3: Scroll Frame (Expands)
        # Row 4: Bottom Frame (Fixed)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- PTF SECTION ---
        self.lbl_ptf = ctk.CTkLabel(self, text="PRICING (PTF)", font=("Roboto", 12, "bold"), anchor="w", text_color="gray")
        self.lbl_ptf.grid(row=0, column=0, pady=(15, 5), padx=20, sticky="ew")

        self.ptf_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ptf_frame.grid(row=1, column=0, pady=(0, 15), padx=10, sticky="ew")
        
        # Dropdown
        self.ptf_var = ctk.StringVar(value="Select PTF...")
        self.ptf_dropdown = ctk.CTkOptionMenu(
            self.ptf_frame, 
            variable=self.ptf_var,
            values=[],
            command=self._on_ptf_selected,
            width=100
        )
        self.ptf_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # View Button (Eye)
        self.btn_view_ptf = ctk.CTkButton(
            self.ptf_frame,
            text="👁",
            width=30,
            command=self._on_view_ptf_click,
            fg_color="#444444",
            hover_color="#555555"
        )
        self.btn_view_ptf.pack(side="left", padx=(0, 5))

        # Add Button (+)
        self.btn_add_ptf = ctk.CTkButton(
            self.ptf_frame,
            text="+",
            width=30,
            command=self._on_add_ptf_click
        )
        self.btn_add_ptf.pack(side="right")

        # --- FILES SECTION ---
        self.lbl_files = ctk.CTkLabel(self, text="SUBSCRIBERS", font=("Roboto", 12, "bold"), anchor="w", text_color="gray")
        self.lbl_files.grid(row=2, column=0, pady=(5, 5), padx=20, sticky="ew")

        # Scrollable list area
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)

        # Bottom Frame for Buttons (Split Button)
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 20))
        
        # Context Menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Open File", command=self._ctx_open)
        self.context_menu.add_command(label="Delete File", command=self._ctx_delete)
        
        self.current_ctx_filename = None

    def update_ptf_list(self, files, selected=None):
        """Updates the dropdown values."""
        self.ptf_files = files
        if not files:
            self.ptf_dropdown.configure(values=["No Files"])
            self.ptf_var.set("No Files")
            return

        self.ptf_dropdown.configure(values=files)
        
        if selected and selected in files:
            self.ptf_var.set(selected)
        elif self.ptf_var.get() not in files and files:
            self.ptf_var.set(files[0])
            # Auto-select the first one if current invalid
            self._on_ptf_selected(files[0])

    def _on_ptf_selected(self, choice):
        if choice == "No Files":
            return
        if self.on_ptf_change_callback:
            self.on_ptf_change_callback(choice)

    def _on_add_ptf_click(self):
        if self.on_add_ptf_callback:
            self.on_add_ptf_callback()
            
    def _on_view_ptf_click(self):
        if self.on_view_ptf_callback:
            self.on_view_ptf_callback()

    def set_files(self, file_list):
        """Populates the sidebar with a list of filenames."""
        if sorted(file_list) == sorted(self.current_files):
            return

        self.current_files = list(file_list) # Copy

        # Clear existing
        for btn in self.buttons:
            btn.destroy()
        self.buttons = []

        # Sort for display
        for filename in sorted(file_list):
            btn = ctk.CTkButton(
                self.scroll_frame, 
                text=f"📄 {filename}", 
                anchor="w",
                fg_color="transparent", 
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                command=lambda f=filename: self.on_click(f)
            )
            btn.pack(fill="x", pady=2)
            
            btn.bind("<Double-Button-1>", lambda event, f=filename: self.open_file_externally(f))
            btn.bind("<Button-3>", lambda event, f=filename: self.show_context_menu(event, f))
            
            self.buttons.append(btn)

    def show_context_menu(self, event, filename):
        self.current_ctx_filename = filename
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _ctx_open(self):
        if self.current_ctx_filename:
            self.open_file_externally(self.current_ctx_filename)
            
    def _ctx_delete(self):
        if self.current_ctx_filename and self.on_delete_file_callback:
            self.on_delete_file_callback(self.current_ctx_filename)

    def open_file_externally(self, filename):
        if self.on_open_file_callback:
            self.on_open_file_callback(filename)

    def on_click(self, filename):
        if self.on_file_select_callback:
            self.on_file_select_callback(filename)
