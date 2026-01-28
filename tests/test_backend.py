import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Add src to pythonpath so we can import modules
sys.path.append(os.path.join(os.getcwd(), 'src'))

from backend.processor import ExcelProcessor
from backend.tariff import TariffManager

def generate_dummy_excel(filename="test_data.xlsx"):
    print(f"Generating dummy data: {filename}")
    
    # Create sample data
    # Columns: Abone No, Date, Consumption
    data = []
    base_time = datetime(2023, 1, 1, 12, 0)
    
    # User 1: "Sub_A" (Peak consumption mostly)
    for i in range(10):
        t = base_time + timedelta(hours=i) # 12:00 to 22:00
        # Peak starts at 17:00
        cons = 10.0
        data.append({"Abone No": "Sub_A", "Date": t, "Consumption": cons})

    # User 2: "Sub_B" (Night consumption mostly)
    for i in range(10):
        t = base_time + timedelta(hours=i+12) # 00:00 onwards
        cons = 5.0
        data.append({"Abone No": "Sub_B", "Date": t, "Consumption": cons})

    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print("Dummy file created.")
    return filename

def test_backend_logic():
    print("\n--- Testing Backend Logic ---")
    
    # 1. Setup
    filename = generate_dummy_excel()
    processor = ExcelProcessor()
    
    # 2. Load
    success, msg = processor.load_file(filename)
    if not success:
        print(f"FAILED to load: {msg}")
        return
    print("File loaded successfully.")

    # 3. Split
    success, msg = processor.split_data("Abone No")
    if not success:
        print(f"FAILED to split: {msg}")
        return
    print(f"Split successfully: {msg}")
    
    if "Sub_A" not in processor.split_files or "Sub_B" not in processor.split_files:
        print("FAILED: Expected split keys 'Sub_A' and 'Sub_B' not found.")
        return

    # 4. Calculation Verification
    # Check Sub_A data
    df_a = processor.get_file_data("Sub_A")
    # We expect some Peak pricing (17:00-22:00) and Day pricing (12:00-17:00)
    # Default Rates: Day=1.5, Peak=2.5
    
    print("\nVerifying Sub_A Calculations:")
    for _, row in df_a.iterrows():
        t = row["Date"]
        cost = row["Calculated Cost (TL)"]
        unit_price = row["Unit Price (TL)"]
        print(f"  Time: {t.time()} | Cons: {row['Consumption']} | Price: {unit_price} | Cost: {cost}")
        
        # Simple assertions
        hour = t.hour
        expected_rate = 1.5
        if 17 <= hour < 22:
            expected_rate = 2.5
        elif hour >= 22 or hour < 6:
            expected_rate = 0.8
            
        if abs(unit_price - expected_rate) > 0.01:
            print(f"  ERROR: Expected rate {expected_rate} but got {unit_price}")

    # 5. Save
    saved_count = processor.save_split_files("output_test")
    print(f"\nSaved {saved_count} files to 'output_test' directory.")
    
    if os.path.exists("output_test/Sub_A.xlsx"):
        print("Verification: Sub_A.xlsx exists.")
    else:
        print("Verification FAILED: Sub_A.xlsx missing.")

    # Clean up
    # os.remove(filename)
    print("\n--- Backend Test Complete ---")

if __name__ == "__main__":
    test_backend_logic()
