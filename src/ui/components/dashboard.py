import customtkinter as ctk
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tksheet import Sheet

class Dashboard(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Grid layout for Dashboard
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Stats
        self.grid_rowconfigure(1, weight=1) # Main Content

        # 1. Stats Panel
        self.stats_frame = ctk.CTkFrame(self, height=60, corner_radius=5)
        self.stats_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        self.lbl_total_cons = ctk.CTkLabel(self.stats_frame, text="Total Consumption: 0 kWh", font=("Arial", 14, "bold"))
        self.lbl_total_cons.pack(side="left", padx=20, pady=10)
        
        self.lbl_total_cost = ctk.CTkLabel(self.stats_frame, text="Total Cost: 0.00 TL", font=("Arial", 14, "bold"), text_color="#4CAF50")
        self.lbl_total_cost.pack(side="right", padx=20, pady=10)

        # 2. Tabview for Visualization / Data
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        self.tab_viz = self.tabview.add("Visualization")
        self.tab_data = self.tabview.add("Data Editor")
        
        # --- Visualization Tab ---
        self.tab_viz.grid_columnconfigure(0, weight=1)
        self.tab_viz.grid_rowconfigure(0, weight=1)
        
        self.graph_frame = ctk.CTkFrame(self.tab_viz, fg_color="transparent")
        self.graph_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # --- Data Editor Tab ---
        self.tab_data.grid_columnconfigure(0, weight=1)
        self.tab_data.grid_rowconfigure(0, weight=1) # Sheet
        self.tab_data.grid_rowconfigure(1, weight=0) # Buttons
        
        # tksheet Frame
        self.sheet_frame = ctk.CTkFrame(self.tab_data)
        self.sheet_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        self.sheet = Sheet(self.sheet_frame,
                           show_table=True,
                           show_top_left=True,
                           show_row_index=True,
                           show_header=True,
                           show_x_scrollbar=True,
                           show_y_scrollbar=True,
                           empty_horizontal=0, 
                           empty_vertical=0,
                           header_font=("Arial", 10, "bold"),
                           table_bg="#2b2b2b",
                           header_bg="#333333",
                           index_bg="#333333",
                           header_fg="white",
                           index_fg="white",
                           table_fg="#d4d4d4",
                           table_grid_fg="#555555",
                           table_selected_box_bg="#1f77b4",
                           table_selected_box_fg="white")
        
        self.sheet.pack(fill="both", expand=True)
        self.sheet.enable_bindings(("single_select", 
                                    "drag_select", 
                                    "column_drag_and_drop",
                                    "row_drag_and_drop",
                                    "column_select",
                                    "row_select",
                                    "column_width_resize",
                                    "double_click_column_resize",
                                    "row_width_resize",
                                    "column_height_resize",
                                    "arrowkeys",
                                    "row_height_resize",
                                    "double_click_row_resize",
                                    "right_click_popup_menu",
                                    "rc_select",
                                    "rc_insert_column",
                                    "rc_delete_column",
                                    "rc_insert_row",
                                    "rc_delete_row",
                                    "copy",
                                    "cut",
                                    "paste",
                                    "delete",
                                    "undo",
                                    "edit_cell"))

        # Action Buttons for Data Grid
        self.actions_frame = ctk.CTkFrame(self.tab_data, height=40, fg_color="transparent")
        self.actions_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        self.btn_save_changes = ctk.CTkButton(self.actions_frame, text="💾 Save Changes & Recalculate", command=self.save_changes)
        self.btn_save_changes.pack(side="right")
        
        self.current_df = None
        self.current_filename = None
        self.on_save_callback = None

    def set_save_callback(self, callback):
        self.on_save_callback = callback

    def load_data(self, df, filename=None):
        """Updates the dashboard with dataframe data."""
        self.current_df = df
        self.current_filename = filename

        if df is None or df.empty:
            return

        # Update Stats
        # Try to find consumption and cost columns
        cols = {c.lower(): c for c in df.columns}
        # Consumption
        cons_col = cols.get('aktif çekiş') or cols.get('consumption') or cols.get('tuketim') or cols.get('amount')
        
        # Cost (Check for new PTF cost column first, then fallback)
        ptf_cost_col = "PTF Kaynaklı Tutar"
        old_cost_col = 'Calculated Cost (TL)'
        
        cost_col = ptf_cost_col if ptf_cost_col in df.columns else old_cost_col

        total_cons = df[cons_col].sum() if cons_col and cons_col in df else 0
        total_cost = df[cost_col].sum() if cost_col in df else 0

        self.lbl_total_cons.configure(text=f"Total Consumption: {total_cons:,.2f} kWh")
        self.lbl_total_cost.configure(text=f"Total Cost: {total_cost:,.2f} TL")

        # Update Graph
        self.ax.clear()
        date_col = cols.get('date') or cols.get('tarih')
        
        if date_col and cons_col and date_col in df and cons_col in df:
            # Sort by date for plotting
            plot_df = df.sort_values(by=date_col)
            self.ax.plot(plot_df[date_col], plot_df[cons_col], marker='o', linestyle='-', color='#3B8ED0')
            self.ax.set_title("Consumption Over Time")
            self.ax.set_xlabel("Date")
            self.ax.set_ylabel("Consumption (kWh)")
            self.ax.grid(True, linestyle='--', alpha=0.6)
            self.figure.autofmt_xdate()
        else:
            self.ax.text(0.5, 0.5, "Missing 'Date' or 'Consumption' columns for graph.", 
                         horizontalalignment='center', verticalalignment='center')
        
        self.canvas.draw()

        # Update Data Table using tksheet
        self._populate_grid(df)

    def _populate_grid(self, df):
        if df is None:
            return
            
        # Set headers
        headers = list(df.columns)
        self.sheet.headers(headers)
        
        # Set data (convert to list of lists)
        data = df.values.tolist()
        self.sheet.set_sheet_data(data)

    def save_changes(self):
        """
        Reads values from the UI grid, updates the DataFrame,
        Triggers the callback to recalculate and save to disk.
        """
        if self.current_df is None:
            return

        try:
            # Get data from tksheet
            # .get_sheet_data() returns list of lists
            data = self.sheet.get_sheet_data()
            
            # Reconstruct DataFrame (keeping original columns)
            # Note: This assumes column order/count hasn't changed. 
            # If user added columns via sheet, we might need to handle headers.
            headers = self.sheet.headers()
            
            # Create new DF from sheet data
            new_df = pd.DataFrame(data, columns=headers)
            
            # Attempt to convert types (tksheet returns strings usually, or mixed)
            # We try to infer objects
            new_df = new_df.infer_objects()
            
            # Specifically try to convert numeric columns back to numeric
            for col in new_df.columns:
                try:
                    new_df[col] = pd.to_numeric(new_df[col])
                except:
                    pass
            
            # Notify App to re-process and save
            if self.on_save_callback and self.current_filename:
                self.on_save_callback(self.current_filename, new_df)
                
        except Exception as e:
            print(f"Error saving grid changes: {e}")
