import customtkinter
import sys
import os

# Add src to path if needed (though usually not if running from root with -m)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui import AutoTitleApp

def main():
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    
    app = AutoTitleApp()
    app.mainloop()

if __name__ == "__main__":
    main()
