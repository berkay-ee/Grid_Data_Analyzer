import PyInstaller.__main__
import os
import shutil
import customtkinter

def build_exe():
    # Get the location of customtkinter to include its assets
    ctk_path = os.path.dirname(customtkinter.__file__)
    
    # Define the separator for --add-data (semicolon for Windows, colon for Unix)
    # Since the user will run this on Windows, it should likely use ';'.
    # However, PyInstaller is smart enough to handle this if we use the API, 
    # OR we can detect os.name. 
    # Since I am writing a script intended to be run ON the target machine (Windows),
    # I should use os.pathsep.
    
    add_data_separator = os.pathsep
    
    # Construct the add-data argument
    # We need to copy the entire customtkinter folder to customtkinter in the bundle
    ctk_data = f'{ctk_path}{add_data_separator}customtkinter'

    print("Building Apollo Splitter executable...")
    print(f"CustomTkinter path: {ctk_path}")
    
    # PyInstaller arguments
    args = [
        'main.py',                        # Your entry point
        '--name=ApolloSplitter',          # Name of the executable
        '--noconsole',                    # No terminal window (GUI only)
        '--onefile',                      # Bundle everything into a single .exe
        '--clean',                        # Clean cache
        f'--add-data={ctk_data}',         # Include CTK assets
        # We might need to handle other hidden imports if they occur, 
        # but CTK is the main one requiring asset copying.
        '--collect-all=customtkinter',    # Ensure all submodules are collected
        '--collect-all=eptr2',            # Ensure eptr2 is collected
        '--collect-all=pywebview',        # Ensure pywebview is collected
        '--hidden-import=babel.numbers',  # Common hidden import needed for some pandas/plotting
    ]
    
    # Run PyInstaller
    PyInstaller.__main__.run(args)
    
    print("\nBuild complete!")
    print(f"Check the 'dist' folder for your executable.")

if __name__ == "__main__":
    build_exe()
