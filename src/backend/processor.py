import pandas as pd
import os
import shutil
from datetime import datetime
from src.backend.tariff import TariffManager

class ExcelProcessor:
    PTF_DIR = "PTF_Files"

    def __init__(self):
        self.tariff_manager = TariffManager()
        self.current_df = None
        self.ptf_df = None
        self.split_files = {}  # Dictionary to store {filename: dataframe}
        
        # Ensure PTF directory exists
        if not os.path.exists(self.PTF_DIR):
            try:
                os.makedirs(self.PTF_DIR)
            except OSError as e:
                print(f"Error creating PTF directory: {e}")

    def get_available_ptf_files(self):
        """Returns a list of available PTF Excel files in the library."""
        if not os.path.exists(self.PTF_DIR):
            return []
        return [f for f in os.listdir(self.PTF_DIR) if f.endswith(('.xlsx', '.xls'))]

    def import_ptf_to_library(self, filepath):
        """Copies a user-selected file into the PTF library."""
        if not os.path.exists(filepath):
            return False, "Source file not found."
            
        try:
            filename = os.path.basename(filepath)
            dest_path = os.path.join(self.PTF_DIR, filename)
            shutil.copy2(filepath, dest_path)
            return True, f"Imported {filename} to library."
        except Exception as e:
            return False, f"Import failed: {e}"

    def load_file(self, filepath):
        """Loads an Excel file into a pandas DataFrame (Consumption Data)."""
        try:
            # Load with openpyxl engine
            df = pd.read_excel(filepath, engine='openpyxl')
            
            # clean column names (strip whitespace)
            df.columns = df.columns.str.strip()
            self.current_df = df
            
            # Attempt auto-merge if PTF is already loaded
            if self.ptf_df is not None:
                self._apply_ptf_merge()

            return True, f"Loaded {len(self.current_df)} rows."
        except Exception as e:
            return False, str(e)

    def load_ptf_file(self, filename_or_path):
        """Loads a PTF file. Accepts either a filename in library or full path."""
        try:
            # Determine path
            if os.path.exists(filename_or_path):
                filepath = filename_or_path
            else:
                filepath = os.path.join(self.PTF_DIR, filename_or_path)
                
            if not os.path.exists(filepath):
                return False, f"File not found: {filepath}"

            df = pd.read_excel(filepath, engine='openpyxl')
            df.columns = df.columns.str.strip()
            
            # Validation
            required = ['Tarih', 'Saat', 'PTF (TL/MWh)']
            missing = [col for col in required if col not in df.columns]
            if missing:
                return False, f"Missing columns in PTF file: {missing}"
            
            self.ptf_df = df
            
            # Attempt auto-merge if Consumption is already loaded
            if self.current_df is not None:
                self._apply_ptf_merge()
                
            return True, f"Loaded PTF Data: {len(df)} rows."
        except Exception as e:
            return False, str(e)

    def _apply_ptf_merge(self):
        """Merges PTF data into the current consumption dataframe."""
        if self.current_df is None or self.ptf_df is None:
            return

        try:
            # We merge on 'Tarih' and 'Saat'. 
            # Note: We assume formats match (e.g. Strings or Datetime objects).
            # To be safe, we could normalize them, but we'll try direct merge first 
            # as validated in tests.
            
            # Check if already merged to avoid duplicates
            if "PTF (TL/MWh)" in self.current_df.columns:
                 # Drop old PTF columns to re-merge
                 cols_to_drop = [c for c in self.ptf_df.columns if c in self.current_df.columns and c not in ['Tarih', 'Saat']]
                 self.current_df.drop(columns=cols_to_drop, inplace=True, errors='ignore')

            merged = pd.merge(self.current_df, self.ptf_df, on=["Tarih", "Saat"], how="left")
            self.current_df = merged
        except Exception as e:
            print(f"Merge error: {e}")

    def split_data(self, group_col="Abone No"):
        """Splits the loaded DataFrame by the specified column."""
        if self.current_df is None:
            return False, "No data loaded."
        
        if group_col not in self.current_df.columns:
            return False, f"Column '{group_col}' not found in Excel file."

        self.split_files = {}
        unique_groups = self.current_df[group_col].unique()

        for group in unique_groups:
            # Create a copy to avoid SettingWithCopy warnings
            sub_df = self.current_df[self.current_df[group_col] == group].copy()
            
            # Generate a safe filename
            safe_name = str(group).replace("/", "_").replace("\\", "_")
            self.split_files[safe_name] = sub_df

        return True, f"Split into {len(self.split_files)} files."

    def calculate_costs(self, df):
        """
        Calculates Costs. 
        Priority: 
        1. PTF Logic (if PTF columns exist)
        2. TariffManager Logic (fallback)
        """
        if df is None or df.empty:
            return df
            
        # 1. PTF Logic
        if "PTF (TL/MWh)" in df.columns:
            # Identify Consumption Column
            cols = {c.lower(): c for c in df.columns}
            cons_col = cols.get('aktif çekiş') or cols.get('consumption') or cols.get('toplam (kwh)')
            
            if cons_col:
                # Gerçek Tüketim (MWh) = Aktif Çekiş / 1000
                df["Gerçek Tüketim (MWh)"] = df[cons_col] / 1000.0
                
                # PTF Cost = Consumption (MWh) * PTF Price
                df["PTF Kaynaklı Tutar"] = df["Gerçek Tüketim (MWh)"] * df["PTF (TL/MWh)"]
                
                return df

        # 2. Fallback Logic (Old TariffManager)
        # Identify columns (case-insensitive search)
        cols = {c.lower(): c for c in df.columns}
        
        date_col = cols.get('date') or cols.get('tarih') or cols.get('time') or cols.get('zaman')
        cons_col = cols.get('consumption') or cols.get('tuketim') or cols.get('amount') or cols.get('miktar')

        if not date_col or not cons_col:
            return df

        # Ensure Date column is datetime
        try:
            # Working on a copy if needed, but here we modify in place
            # Check if it's already datetime to avoid errors
            if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
                 df[date_col] = pd.to_datetime(df[date_col])
        except:
            return df 

        # Calculate Cost
        def get_cost(row):
            usage = row[cons_col]
            dt = row[date_col]
            if pd.isna(usage) or pd.isna(dt):
                return 0.0
            price = self.tariff_manager.get_price(dt)
            return usage * price

        if 'Unit Price (TL)' not in df.columns:
            df['Unit Price (TL)'] = df[date_col].apply(lambda x: self.tariff_manager.get_price(x) if pd.notnull(x) else 0)
        
        if 'Calculated Cost (TL)' not in df.columns:
            df['Calculated Cost (TL)'] = df.apply(get_cost, axis=1)
        
        return df

    def get_file_data(self, filename):
        """Returns the dataframe for a specific split file, with calculations applied."""
        if filename in self.split_files:
            df = self.split_files[filename]
            return self.calculate_costs(df)
        return None

    def save_split_files(self, base_output_dir, source_filename=None):
        """
        Saves all split dataframes to Excel files.
        Hierarchy: base_output_dir / source_filename / split_files...
        """
        # Determine actual output directory
        if source_filename:
            # Strip extension if present
            folder_name = os.path.splitext(source_filename)[0]
            target_dir = os.path.join(base_output_dir, folder_name)
        else:
            target_dir = base_output_dir

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        saved_count = 0
        for name, df in self.split_files.items():
            # Apply calculations before saving
            processed_df = self.calculate_costs(df)
            
            output_path = os.path.join(target_dir, f"{name}.xlsx")
            processed_df.to_excel(output_path, index=False)
            saved_count += 1
        
        # Return both count and the directory used, so UI can update sidebar
        return saved_count, target_dir
