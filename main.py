import sys
import tkinter as tk

from DroneNetwork import DroneNetwork
from gui import DroneSimulationGUI
from parser import Parser

if __name__ == "__main__":
    if len(sys.argv) > 1:
        dn = DroneNetwork()
        ps = Parser()
        filename = None
        gui = False
        for arg in sys.argv[1:]:
            if arg == "-g":
                gui = True
            else:
                filename = arg
        if filename is None:
            print("Usage: uv run python gui.py <file> (-g)")
            sys.exit(0)
        try:
            ps.parse_file(dn, filename)
            ps.validate(dn)
            dn.init_drone()
            dn.precalculate_all_turns()
            dn.print_result()
            if gui:
                root = tk.Tk()
                simGui = DroneSimulationGUI(root, dn)
                root.mainloop()
        except Exception as e:
            print(f"Error: {e}")
        except KeyboardInterrupt:
            pass
    else:
        print("Usage: uv run python gui.py <file>")
