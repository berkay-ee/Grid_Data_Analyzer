from src.ui.app import App
import multiprocessing

if __name__ == "__main__":
    # Required for PyInstaller executables on Windows to support multiprocessing
    multiprocessing.freeze_support()
    
    app = App()
    app.mainloop()
