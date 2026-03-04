import multiprocessing
import traceback

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    try:
        print("1. Importing App...")
        from src.ui.app import App
        
        print("2. Initializing App...")
        app = App()
        
        print("3. Starting Mainloop...")
        app.mainloop()
        
    except Exception as e:
        print("\n" + "="*50)
        print("🚨 CRITICAL ERROR DETECTED 🚨")
        print("="*50)
        traceback.print_exc()
        print("="*50)
        input("Press ENTER to close this window...") # This prevents the terminal from auto-closing