# Main execution
import tkinter as Tk
from controller import AppController

if __name__ == "__main__":
    root = Tk.Tk()
    app = AppController(root)
    app.run()
