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
        self.split_files = {}

        if not os.path.exists(self.PTF_DIR):
            try:
                os.makedirs(self.PTF_DIR)
            except OSError as e:
                print(f"Error creating PTF directory: {e}")

    def _clean_numeric_column(self, df, column_name):
        """Converts Turkish decimals (9,66) to floats (9.66)."""
        if column_name in df.columns:
            if df[column_name].dtype == 'object':
                df[column_name] = df[column_name].astype(str).str.replace(',', '.').astype(float)
        return df

    def _cleanup_final_columns(self, df):
        """
        Removes 'noise' columns (Reaktif, Veriş, Oran) to match the clean screenshot.
        """
        # Keywords for columns we generally want to REMOVE
        drop_keywords = ['reaktif', 'kapasitif', 'indüktif', 'veriş', 'oran', 'tanım', 'veri']
        
        # Keywords for columns we MUST KEEP (Protects them from accidental deletion)
        keep_keywords = ['abone', 'ünvan', 'tarih', 'saat', 'aktif çekiş', 'ptf', 'gerçek', 'tutar']
        
        cols_to_drop = []
        for col in df.columns:
            c_lower = col.lower()
            # If column has a "bad" keyword AND doesn't have a "good" keyword
            if any(bad in c_lower for bad in drop_keywords) and not any(good in c_lower for good in keep_keywords):
                cols_to_drop.append(col)
        
        if cols_to_drop:
            df.drop(columns=cols_to_drop, inplace=True, errors='ignore')
            
        return df

    def _normalize_keys(self, df, is_ptf=False):
        """
        Converts everything to String 'YYYY-MM-DD' and Integer Hour.
        Handles HH:MM, HH:MM:SS, and Integer formats automatically.
        """
        # 1. Find Columns
        col_map = {c.lower(): c for c in df.columns}
        t_col = col_map.get('tarih') or col_map.get('date') or col_map.get('zaman')
        s_col = col_map.get('saat') or col_map.get('time') or col_map.get('hour')

        # 2. Smart Extract: If 'Saat' is missing, try to get it from 'Tarih'
        if not is_ptf and t_col and not s_col:
            try:
                # Force string conversion first to preserve time info
                df['Temp_Str'] = df[t_col].astype(str)
                temp_dt = pd.to_datetime(df['Temp_Str'], dayfirst=True, errors='coerce')
                
                if temp_dt.dt.hour.notna().any() and temp_dt.dt.hour.sum() > 0:
                    df['Temp_Saat_Extracted'] = temp_dt.dt.hour.fillna(0).astype(int)
                    s_col = 'Temp_Saat_Extracted'
                
                df.drop(columns=['Temp_Str'], inplace=True, errors='ignore')
            except:
                pass

        if not t_col or not s_col:
            return df, False, "Missing Columns"

        # 3. Create Standardized Merge Keys
        try:
            # Date -> String "2026-01-01"
            df['Merge_Tarih'] = pd.to_datetime(df[t_col], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
        except Exception as e:
            return df, False, f"Date Error: {e}"

        try:
            # Time -> Integer 0-23
            df['Merge_Saat'] = pd.to_numeric(df[s_col], errors='coerce').fillna(-1).astype(int)
            mask_fail = df['Merge_Saat'] == -1
            if mask_fail.any():
                df.loc[mask_fail, 'Merge_Saat'] = pd.to_datetime(
                    df.loc[mask_fail, s_col].astype(str), errors='coerce'
                ).dt.hour.fillna(0).astype(int)
        except Exception as e:
            return df, False, f"Time Error: {e}"

        if s_col == 'Temp_Saat_Extracted':
            df.drop(columns=['Temp_Saat_Extracted'], inplace=True, errors='ignore')

        return df, True, "OK"

    def calculate_costs(self, df):
        """Calculates Consumption * PTF."""
        if df is None or df.empty: return df

        cols = {c.lower(): c for c in df.columns}
        cons_col = cols.get('aktif çekiş') or cols.get('consumption') or cols.get('toplam (kwh)')
        ptf_col = cols.get('ptf (tl/mwh)')

        # Ensure numeric conversion happens before math
        if cons_col: df = self._clean_numeric_column(df, cons_col)
        if ptf_col: df = self._clean_numeric_column(df, ptf_col)

        if cons_col and ptf_col:
            df["Gerçek Tüketim (MWh)"] = df[cons_col] / 1000.0
            df["PTF x Gerçekleşen Tüketim"] = (df["Gerçek Tüketim (MWh)"] * df[ptf_col]).round(2)
        
        return df

    def get_file_data(self, filename):
        """Returns the dataframe for a specific split file (used by UI)."""
        name_key = os.path.splitext(filename)[0]
        if name_key in self.split_files:
            return self.calculate_costs(self.split_files[name_key])
        if filename in self.split_files:
            return self.calculate_costs(self.split_files[filename])
        return None

    def calculate_ptf_for_folder(self, folder_path):
        """
        Processes files, calculates costs, removes extra columns, and saves.
        Does NOT delete source files.
        """
        if not os.path.exists(folder_path) or self.ptf_df is None:
            return False, "Folder not found or PTF file not loaded."

        parent_dir = os.path.dirname(folder_path)
        output_dir = os.path.join(parent_dir, "PtfHesaplama")
        os.makedirs(output_dir, exist_ok=True)

        files = [f for f in os.listdir(folder_path) if f.endswith(('.xlsx', '.xls'))]
        processed_count = 0
        errors = []

        # --- PREPARE PTF ---
        ptf_ready, valid_ptf, msg = self._normalize_keys(self.ptf_df.copy(), is_ptf=True)
        if not valid_ptf:
            return False, f"PTF File Error: {msg}"
        
        # Remove duplicates to avoid 1-to-many explosion
        ptf_clean = ptf_ready[['Merge_Tarih', 'Merge_Saat', 'PTF (TL/MWh)']].drop_duplicates(subset=['Merge_Tarih', 'Merge_Saat'])
        ptf_dates = set(ptf_clean['Merge_Tarih'].unique())

        for filename in files:
            try:
                file_path = os.path.join(folder_path, filename)
                df = pd.read_excel(file_path, engine='openpyxl')
                df.columns = df.columns.str.strip()

                # --- PREPARE SUBSCRIBER ---
                df_ready, valid, msg = self._normalize_keys(df.copy(), is_ptf=False)
                if not valid:
                    errors.append(f"{filename}: {msg}")
                    continue

                # Check overlap
                file_dates = set(df_ready['Merge_Tarih'].unique())
                if not file_dates.intersection(ptf_dates):
                    sample_file_date = list(file_dates)[0] if file_dates else "Unknown"
                    print(f"WARNING: {filename} ({sample_file_date}) outside PTF range. Skipping.")
                    continue

                # --- MERGE ---
                merged = pd.merge(df_ready, ptf_clean, on=['Merge_Tarih', 'Merge_Saat'], how='left')
                
                # --- CALCULATE ---
                final_df = self.calculate_costs(merged)

                # --- CLEANUP COLUMNS ---
                final_df.drop(columns=['Merge_Tarih', 'Merge_Saat'], inplace=True, errors='ignore')
                final_df = self._cleanup_final_columns(final_df)  # Remove Reaktif/Veriş/etc.

                final_df.to_excel(os.path.join(output_dir, filename), index=False)
                processed_count += 1
                
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")

        if processed_count == 0 and errors:
            return False, f"Errors: {'; '.join(errors[:2])}"
        if processed_count == 0:
            return False, "No Matching Dates found."
            
        return True, f"Success! Processed {processed_count} files."

    # --- Standard Methods ---
    def get_available_ptf_files(self):
        if not os.path.exists(self.PTF_DIR): return []
        return [f for f in os.listdir(self.PTF_DIR) if f.endswith(('.xlsx', '.xls'))]

    def import_ptf_to_library(self, filepath):
        if not os.path.exists(filepath): return False, "File not found."
        try:
            filename = os.path.basename(filepath)
            dest_path = os.path.join(self.PTF_DIR, filename)
            shutil.copy2(filepath, dest_path)
            return True, f"Imported {filename}."
        except Exception as e: return False, str(e)

    def load_file(self, filepath):
        try:
            self.current_df = pd.read_excel(filepath, engine='openpyxl')
            self.current_df.columns = self.current_df.columns.str.strip()
            return True, f"Loaded {len(self.current_df)} rows."
        except Exception as e: return False, str(e)

    def load_ptf_file(self, filename_or_path):
        try:
            path = filename_or_path if os.path.exists(filename_or_path) else os.path.join(self.PTF_DIR, filename_or_path)
            self.ptf_df = pd.read_excel(path, engine='openpyxl')
            self.ptf_df.columns = self.ptf_df.columns.str.strip()
            return True, "PTF Loaded."
        except Exception as e: return False, str(e)

    def split_data(self, group_col="Abone No"):
        if self.current_df is None: return False, "No data."
        if group_col not in self.current_df.columns: return False, f"Missing {group_col}"
        self.split_files = {}
        for group in self.current_df[group_col].unique():
            self.split_files[str(group).replace("/", "_")] = self.current_df[self.current_df[group_col] == group].copy()
        return True, f"Split {len(self.split_files)} files."
    
    def save_split_files(self, base_dir, source_name="Data"):
        folder_name = os.path.splitext(source_name)[0]
        target_dir = os.path.join(base_dir, folder_name, "AboneNo")
        os.makedirs(target_dir, exist_ok=True)
        for name, df in self.split_files.items():
            # Clean columns before saving initial split files too
            clean_df = self._cleanup_final_columns(df.copy())
            clean_df.to_excel(os.path.join(target_dir, f"{name}.xlsx"), index=False)
        return len(self.split_files), target_dir