import customtkinter as ctk
import os
import time
from datetime import datetime
from tkinter import filedialog, messagebox

# Import Components
from src.ui.components.sidebar import Sidebar
from src.ui.components.dashboard import Dashboard
from src.ui.components.settings import Settings
from src.ui.components.webview import WebView
from src.backend.processor import ExcelProcessor

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("Apollo Splitter & Visualizer")
        self.geometry("1100x700")

        # --- Backend Setup ---
        self.processor = ExcelProcessor()
        
        # --- Grid Layout ---
        self.grid_columnconfigure(0, weight=0)  # Activity Bar (Left Strip)
        self.grid_columnconfigure(1, weight=0)  # Sidebar (File List)
        self.grid_columnconfigure(2, weight=1)  # Main Content
        self.grid_rowconfigure(0, weight=1)

        # --- 1. Activity Bar (Far Left) ---
        self.activity_bar = ctk.CTkFrame(self, width=50, corner_radius=0, fg_color="#1e1e1e")
        self.activity_bar.grid(row=0, column=0, sticky="nsew")
        self.activity_bar.grid_propagate(False)

        # Icons (Using text for now, can be replaced with images)
        self.btn_files = self.create_activity_btn("📁", self.show_files_view)
        self.btn_files.pack(pady=(20, 10))

        self.btn_web = self.create_activity_btn("🌐", self.show_web_view)
        self.btn_web.pack(pady=10)
        
        self.btn_settings = self.create_activity_btn("⚙️", self.show_settings_view)
        self.btn_settings.pack(pady=10)

        # --- 2. Sidebar (Middle Left) ---
        self.sidebar = Sidebar(
            self, 
            on_file_select_callback=self.on_file_selected, 
            on_open_file_callback=self.on_file_open_request,
            on_delete_file_callback=self.on_file_delete_request,
            on_ptf_change_callback=self.on_ptf_changed,
            on_add_ptf_callback=self.on_add_ptf,
            on_view_ptf_callback=self.on_view_ptf,
            width=200, 
            corner_radius=0
        )
        self.sidebar.grid(row=0, column=1, sticky="nsew")

        # --- 3. Main Content (Right) ---
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_area.grid(row=0, column=2, sticky="nsew")
        
        # Views
        self.dashboard_view = Dashboard(self.main_area)
        self.dashboard_view.set_save_callback(self.on_dashboard_save)
        
        self.settings_view = Settings(self.main_area, self.processor.tariff_manager)
        self.web_view = WebView(self.main_area)
        
        # --- 4. Console / Status Panel (Bottom) ---
        self.console_frame = ctk.CTkFrame(self, height=100, corner_radius=0, fg_color="#1e1e1e")
        self.console_frame.grid(row=1, column=0, columnspan=3, sticky="nsew")
        self.console_frame.grid_propagate(False) # Fixed height
        
        self.console_label = ctk.CTkLabel(self.console_frame, text="TERMINAL", font=("Consolas", 12, "bold"), text_color="gray")
        self.console_label.pack(anchor="w", padx=10, pady=(5,0))
        
        self.console_text = ctk.CTkTextbox(self.console_frame, font=("Consolas", 12), text_color="#d4d4d4", fg_color="transparent")
        self.console_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.log("Ready.")

        # Initial View
        self.show_files_view()
        
        # State tracking
        # Initialize default output directory
        self.output_directory = os.path.join(os.getcwd(), "Output")
        if not os.path.exists(self.output_directory):
            try:
                os.makedirs(self.output_directory)
                self.log(f"Created default output directory: {self.output_directory}")
            except OSError as e:
                self.log(f"Error creating output directory: {e}")

        # Add "Import Consumption" button to sidebar bottom_frame
        # The PTF buttons are now handled inside the Sidebar class itself
        self.btn_open = ctk.CTkButton(self.sidebar.bottom_frame, text="2. Import Consumption & Split", command=self.import_file)
        self.btn_open.pack(fill="x", pady=(0, 5))

        self.btn_calc = ctk.CTkButton(self.sidebar.bottom_frame, text="3. Calculate PTF for Folder", command=self.calculate_ptf_folder)
        self.btn_calc.pack(fill="x", pady=0)

        # Initialize PTF List
        self.refresh_ptf_list()

        # Start monitoring the output folder
        # self.monitor_output_folder() # Temporarily disabled automatic monitoring as folders change dynamically

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console_text.insert("end", f"[{timestamp}] {message}\n")
        self.console_text.see("end")

    def create_activity_btn(self, icon, command):
        return ctk.CTkButton(
            self.activity_bar, 
            text=icon, 
            width=40, 
            height=40, 
            corner_radius=5, 
            fg_color="transparent",
            hover_color="#333333",
            font=("Arial", 20),
            command=command
        )

    def show_files_view(self):
        self.settings_view.pack_forget()
        self.web_view.pack_forget()
        self.dashboard_view.pack(fill="both", expand=True)

    def show_settings_view(self):
        self.dashboard_view.pack_forget()
        self.web_view.pack_forget()
        self.settings_view.pack(fill="both", expand=True)

    def show_web_view(self):
        self.dashboard_view.pack_forget()
        self.settings_view.pack_forget()
        self.web_view.pack(fill="both", expand=True)
        # Pass the output directory to the web view
        if hasattr(self.web_view, 'update_output_path'):
            self.web_view.update_output_path(self.output_directory)

    # --- PTF HANDLING ---

    def refresh_ptf_list(self, selected=None):
        """Fetches available PTF files from backend and updates sidebar."""
        ptf_files = self.processor.get_available_ptf_files()
        self.sidebar.update_ptf_list(ptf_files, selected)
        
    def on_add_ptf(self):
        """Handler for 'Add' button in PTF section."""
        file_path = filedialog.askopenfilename(title="Import New PTF (Price) File", filetypes=[("Excel Files", "*.xlsx *.xls")])
        if not file_path:
            return

        success, msg = self.processor.import_ptf_to_library(file_path)
        if success:
            self.log(msg)
            filename = os.path.basename(file_path)
            self.refresh_ptf_list(selected=filename) # Refresh and select new file
            
            # Auto-view the new PTF file to confirm data
            self.on_view_ptf()
        else:
            self.log(f"Error importing PTF: {msg}")
            messagebox.showerror("Import Error", msg)

    def on_ptf_changed(self, filename):
        """Handler for Dropdown selection change."""
        self.log(f"Loading PTF: {filename}...")
        success, msg = self.processor.load_ptf_file(filename)
        if success:
            self.log(f"PTF Loaded Successfully.")
        else:
            self.log(f"Error loading PTF: {msg}")
            messagebox.showerror("Error", f"Could not load PTF file: {msg}")
            
    def on_view_ptf(self):
        """Handler for 'Eye' button to view current PTF data."""
        # 1. Switch to dashboard
        self.show_files_view()
        
        # 2. Get current PTF data
        if self.processor.ptf_df is not None:
            # We display the PTF dataframe. 
            # Note: We pass a special filename to indicate it's PTF data (read-only mostly, but editable technically)
            self.dashboard_view.load_data(self.processor.ptf_df, filename="[PTF Data]")
            self.log("Displaying PTF Data.")
            # Switch tab to Data Editor automatically since graphs might not make sense or require specific columns
            self.dashboard_view.tabview.set("Data Editor")
        else:
            messagebox.showinfo("Info", "No PTF data loaded yet.\nPlease select or import a file.")

    # --- FILE HANDLING ---

    def monitor_output_folder(self):
        """Checks the output directory for files and updates the sidebar."""
        # NOTE: With the new hierarchy, simply monitoring 'Output' isn't enough.
        # We need to know WHICH subfolder we are currently looking at.
        # For now, we update the sidebar explicitly after import.
        # If we wanted to monitor, we would need to track 'current_project_folder'.
        pass

    def import_file(self):
        # Warning if PTF not loaded
        if self.processor.ptf_df is None:
            confirm = messagebox.askyesno("Warning", "No PTF Price file selected/loaded.\nCalculations will not be applied.\n\nContinue anyway?")
            if not confirm:
                return

        file_path = filedialog.askopenfilename(title="Select Consumption File", filetypes=[("Excel Files", "*.xlsx *.xls")])
        if not file_path:
            return

        success, msg = self.processor.load_file(file_path)
        if not success:
            messagebox.showerror("Error", f"Failed to load file: {msg}")
            return

        # Perform Split
        split_success, split_msg = self.processor.split_data()
        if split_success:
            self.log(split_msg)
            
            # AUTOMATICALLY DETERMINE OUTPUT FOLDER
            # Create an 'Output' folder in the same directory as the source file (or use global default)
            # Strategy: Use App's default output directory
            base_output_dir = os.path.join(os.getcwd(), "Output")
            
            source_filename = os.path.basename(file_path)

            try:
                # Save files (New Hierarchical Logic)
                count, used_dir = self.processor.save_split_files(base_output_dir, source_filename)
                
                # Update App State
                self.output_directory = used_dir # Now points to Output/MyFile/
                
                # Update Web View
                if hasattr(self.web_view, 'update_output_path'):
                    self.web_view.update_output_path(self.output_directory)

                self.log(f"Saved {count} files to: {self.output_directory}")
                messagebox.showinfo("Success", f"Split complete! {count} files created in:\n{self.output_directory}")
                
                # Update Sidebar
                file_list = list(self.processor.split_files.keys())
                self.sidebar.set_files(file_list)
                
            except Exception as e:
                self.log(f"Error saving files: {e}")
                messagebox.showerror("Error", f"Could not save files: {e}")

        else:
            self.log(f"Error: {split_msg}")
            messagebox.showerror("Error", split_msg)

    def on_file_selected(self, filename):
        # 1. Switch to dashboard view
        self.show_files_view()
        
        # 2. Get data for this file
        
        if filename not in self.processor.split_files:
            # Attempt to load from disk
            file_path = os.path.join(self.output_directory, f"{filename}.xlsx")
            if os.path.exists(file_path):
                try:
                    import pandas as pd
                    df = pd.read_excel(file_path)
                    self.processor.split_files[filename] = df
                    self.log(f"Loaded external file: {filename}")
                except Exception as e:
                    self.log(f"Error loading external file {filename}: {e}")
                    messagebox.showerror("Error", f"Could not load file: {e}")
                    return
            else:
                 messagebox.showerror("Error", f"File not found: {file_path}")
                 return

        df = self.processor.get_file_data(filename)
        
        # 3. Update Dashboard
        self.dashboard_view.load_data(df, filename=filename)

    def on_file_delete_request(self, filename):
        """Deletes the selected file from disk and memory."""
        if not self.output_directory:
            return

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{filename}'?")
        if not confirm:
            return

        file_path = os.path.join(self.output_directory, f"{filename}.xlsx")
        
        # 1. Remove from Disk
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                self.log(f"Deleted file: {filename}")
            except Exception as e:
                self.log(f"Error deleting file: {e}")
                messagebox.showerror("Error", f"Could not delete file: {e}")
                return
        else:
            self.log(f"File not found on disk: {filename}")

        # 2. Remove from Memory
        if filename in self.processor.split_files:
            del self.processor.split_files[filename]
        
        # 3. Update UI
        try:
            # List files again immediately
            files = [f for f in os.listdir(self.output_directory) if f.endswith(('.xlsx', '.xls'))]
            filenames = [os.path.splitext(f)[0] for f in files]
            self.sidebar.set_files(filenames)
            
            # If current view was this file, clear dashboard
            if self.dashboard_view.current_filename == filename:
                self.dashboard_view.load_data(None, None)
                
        except Exception as e:
            pass

    def on_file_open_request(self, filename):
        """Opens the selected file in the system default application."""
        if not self.output_directory:
            messagebox.showwarning("Warning", "Output directory not set.")
            return

        file_path = os.path.join(self.output_directory, f"{filename}.xlsx")
        
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File not found: {file_path}")
            return
            
        try:
            self.log(f"Opening {filename}...")
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # Linux/Mac
                import subprocess
                subprocess.call(('xdg-open', file_path))
        except Exception as e:
            self.log(f"Error opening file: {e}")
            messagebox.showerror("Error", f"Could not open file: {e}")

    def on_dashboard_save(self, filename, updated_df):
        """
        Callback when user clicks 'Save' in Dashboard.
        1. Updates internal DF in processor.
        2. Recalculates Costs (with potentially new tariffs).
        3. Saves specific file to disk.
        """
        # Update the split_files in processor
        self.processor.split_files[filename] = updated_df
        
        # Recalculate costs (in case Tariff or Consumption changed)
        recalc_df = self.processor.calculate_costs(updated_df)
        self.processor.split_files[filename] = recalc_df
        
        # Refresh UI with new calculations
        self.dashboard_view.load_data(recalc_df, filename=filename)
        
        # Save to disk
        if self.output_directory:
            save_path = os.path.join(self.output_directory, f"{filename}.xlsx")
            try:
                recalc_df.to_excel(save_path, index=False)
                self.log(f"Saved changes to {filename} at {save_path}")
                messagebox.showinfo("Saved", f"Changes saved to:\n{save_path}")
            except Exception as e:
                err = f"Failed to save file: {e}"
                self.log(err)
                messagebox.showerror("Save Error", err)
        else:
            messagebox.showwarning("Warning", "Output directory not set. Changes only saved in memory.")

    def calculate_ptf_folder(self):
        """Handler for 'Calculate PTF for Folder' button."""
        # 1. Ensure PTF is loaded
        if self.processor.ptf_df is None:
            messagebox.showwarning("Warning", "No PTF file loaded.\nPlease select a PTF file first.")
            return

        # 2. Select Folder
        # Default to current output directory if exists
        initial_dir = self.output_directory if os.path.exists(self.output_directory) else os.getcwd()
        
        folder_path = filedialog.askdirectory(title="Select Folder containing Subscriber Files", initialdir=initial_dir)
        if not folder_path:
            return

        # 3. Process
        self.log(f"Starting PTF calculation for folder: {folder_path}...")
        success, msg = self.processor.calculate_ptf_for_folder(folder_path)
        
        self.log(msg)
        if success:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)

if __name__ == "__main__":
    app = App()
    app.mainloop()
