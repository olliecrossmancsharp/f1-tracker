import os
import sys
import fastf1 
import pandas as pd
import tkinter as tk

# makes folder for the cache if it exists, doesnt overwrite.  must have admin?
os.makedirs('f1_cache', exist_ok=True)
fastf1.Cache.enable_cache('f1_cache')

print("fetching data")

# gets data from race, season, weekend, race/quali/practice 
session = fastf1.get_session(2019, 'Russia', 'R')
session.load(telemetry=False) #dpes not load telemetry, too big -- maybe add this later?


results = session.results[['DriverNumber', 'Abbreviation', 'FullName', 'ClassifiedPosition']]
penalties = session.race_control_messages[['Category', 'RacingNumber', 'Message']]
root = tk.Tk()
root.title("F1 Session Results")
root.geometry("1600x600")
print(session.race_control_messages.columns.tolist())

canvas = tk.Canvas(root, highlightthickness=0)

# add scrollbar 
scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=scrollbar.set)

# sisplay the canvas and scrollbar
scrollbar.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)

content_frame = tk.Frame(canvas)

canvas_window = canvas.create_window(
    (0, 0),
    window=content_frame,
    anchor="nw"
)

# display race results
label = tk.Label(
    content_frame,
    text=results.to_string(index=False),
    font=("Courier", 10),
    justify="left",
    anchor="nw"
)
label.pack(fill="x", padx=10, pady=5)

# display the penalties and race control messages
label_penalties = tk.Label(
    content_frame,
    text=penalties.to_string(index=False),
    font=("Courier", 10),
    justify="left",
    anchor="nw"
)
label_penalties.pack(fill="x", padx=10, pady=5)

#keep all the content as wide as window
def resize_content(event):
    canvas.itemconfigure(canvas_window, width=event.width)

def update_scroll_region(event):
    canvas.configure(scrollregion=canvas.bbox("all"))
content_frame.bind("<Configure>", update_scroll_region)

# enable mouse wheel scrolling

def on_mousewheel(event):
    if sys.platform == "darwin":
        canvas.yview_scroll(int(-event.delta), "units")
    elif sys.platform == "win32":
        canvas.yview_scroll(int(-event.delta / 120), "units")
    else:
        if event.num == 4:
            canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            canvas.yview_scroll(1, "units")

# windows and mac
canvas.bind_all("<MouseWheel>", on_mousewheel)

# linux mouse wheel
canvas.bind_all("<Button-4>", on_mousewheel)
canvas.bind_all("<Button-5>", on_mousewheel)

canvas.bind("<Configure>", resize_content)
root.mainloop()