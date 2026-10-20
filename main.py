import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import fastf1

# fastF1 setup
cache = os.path.join(os.path.dirname(os.path.abspath(__file__)),"f1_cache")

os.makedirs(cache, exist_ok=True)
fastf1.Cache.enable_cache(cache)


# creqte the main window
root = tk.Tk()
root.title("F1 Session Explorer")
root.geometry("1100x650")
root.minsize(800, 450)

root.columnconfigure(0, weight=1)
root.rowconfigure(2, weight=1)

style = ttk.Style(root)
style.configure("Treeview", rowheight=27)
style.configure("Treeview.Heading", font=("Arial", 10, "bold"))


# session selection controls
controls = ttk.LabelFrame(
    root,
    text="Select a Session",
    padding=10
)
controls.grid(
    row=0, column=0,
    sticky="ew", padx=10, pady=10
)

ttk.Label(controls, text="Season:").grid(
    row=0, column=0, padx=5, pady=5
)

year_var = tk.StringVar(value="2019")

year_entry = ttk.Entry(
    controls,
    textvariable=year_var,
    width=8
)
year_entry.grid(row=0, column=1, padx=5)


ttk.Label(controls, text="Grand Prix:").grid(
    row=0, column=2, padx=5
)

grand_prix_var = tk.StringVar(value="Russia")

grand_prix_entry = ttk.Entry(
    controls,
    textvariable=grand_prix_var,
    width=18
)
grand_prix_entry.grid(row=0, column=3, padx=5)


ttk.Label(controls, text="Session:").grid(
    row=0, column=4, padx=5
)

session_var = tk.StringVar(value="Race")

session_names = {
    "Practice 1": "FP1",
    "Practice 2": "FP2",
    "Practice 3": "FP3",
    "Sprint Qualifying": "SQ",
    "Sprint": "S",
    "Qualifying": "Q",
    "Race": "R"
}

session_box = ttk.Combobox(
    controls,
    textvariable=session_var,
    values=list(session_names.keys()),
    state="readonly",
    width=18
)
session_box.grid(row=0, column=5, padx=5)


# status message
status_var = tk.StringVar(value="Ready to load a session.")

status_label = ttk.Label(
    root,
    textvariable=status_var,
    anchor="w"
)
status_label.grid(
    row=1, column=0,
    sticky="ew", padx=12, pady=(0, 8)
)

# results and race-control tabs
notebook = ttk.Notebook(root)
notebook.grid(
    row=2, column=0,
    sticky="nsew", padx=10, pady=(0, 10)
)

results_tab = ttk.Frame(notebook)
control_tab = ttk.Frame(notebook)

notebook.add(results_tab, text="Race Results")
notebook.add(control_tab, text="Race Control")


def create_table(parent):
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True)

    table = ttk.Treeview(
        frame,
        show="headings"
    )

    vertical_scroll = ttk.Scrollbar(
        frame,
        orient="vertical",
        command=table.yview
    )

    horizontal_scroll = ttk.Scrollbar(
        frame,
        orient="horizontal",
        command=table.xview
    )

    table.configure(
        yscrollcommand=vertical_scroll.set,
        xscrollcommand=horizontal_scroll.set
    )

    table.grid(row=0, column=0, sticky="nsew")
    vertical_scroll.grid(row=0, column=1, sticky="ns")
    horizontal_scroll.grid(row=1, column=0, sticky="ew")

    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    return table


results_table = create_table(results_tab)
control_table = create_table(control_tab)


# populate / sort tables

def display_table(table, dataframe):
    table.delete(*table.get_children())

    columns = list(dataframe.columns)

    table["columns"] = columns

    for column in columns:
        table.heading(
            column,
            text=column,
            command=lambda c=column, t=table:
                sort_table(t, c, False)
        )

        table.column(
            column,
            width=140,
            minwidth=80,
            anchor="w"
        )

    for row in dataframe.itertuples(index=False, name=None):
        values = [
            "" if value is None else str(value)
            for value in row
        ]

        table.insert("", "end", values=values)


def sort_table(table, column, reverse):
    rows = [
        (table.set(item, column), item)
        for item in table.get_children("")
    ]

    def sort_key(item):
        value = item[0]

        try:
            return (0, float(value))
        except (ValueError, TypeError):
            return (1, value.casefold())

    rows.sort(key=sort_key, reverse=reverse)

    for position, (_, item) in enumerate(rows):
        table.move(item, "", position)

    table.heading(
        column,
        command=lambda:
            sort_table(table, column, not reverse)
    )

# Load session data

def load_session():
    try:
        year = int(year_var.get().strip())

        if not 1950 <= year <= 2100:
            raise ValueError

        grand_prix = grand_prix_var.get().strip()

        if not grand_prix:
            messagebox.showerror(
                "Missing Grand Prix",
                "Enter a Grand Prix name by country"
            )
            return

    except ValueError:
        messagebox.showerror(
            "Invalid season",
            "Enter a valid four-digit season year (2018-today)"
        )
        return

    session_code = session_names[session_var.get()]

    load_button.config(state="disabled")
    status_var.set("Fetching session data...")

    worker = threading.Thread(
        target=fetch_session,
        args=(year, grand_prix, session_code),
        daemon=True
    )

    worker.start()


def fetch_session(year, grand_prix, session_code):
    try:
        session = fastf1.get_session(
            year,
            grand_prix,
            session_code
        )
        session.load(telemetry=False)

        results = session.results[
            [
                "DriverNumber",
                "Abbreviation",
                "FullName",
                "ClassifiedPosition"
            ]
        ].copy()

        messages = session.race_control_messages

        if messages is None or messages.empty:
            penalties = None
        else:
            available_columns = [
                column
                for column in [
                    "Category",
                    "RacingNumber",
                    "Message"
                ]
                if column in messages.columns
            ]

            penalties = messages[available_columns].copy()

        # update Tkinter ONLY on its main thread.
        root.after(
            0,
            lambda: show_session(
                results,
                penalties,
                year,
                grand_prix,
                session_code
            )
        )

    except Exception as error:
        root.after(
            0,
            lambda err=str(error): show_error(err)
        )


def show_session(results, penalties, year, grand_prix, session_code):
    """Display the fetched data in the GUI."""

    display_table(results_table, results)

    if penalties is None:
        display_table(
            control_table,
            __import__("pandas").DataFrame(
                columns=["Message"]
            )
        )

        status_var.set(
            f"{year} {grand_prix} | {session_code} | "
            "Loaded; no race-control messages available."
        )
    else:
        display_table(control_table, penalties)

        status_var.set(
            f"{year} {grand_prix} | {session_code} | "
            f"{len(results)} result rows | "
            f"{len(penalties)} race-control messages"
        )

    load_button.config(state="normal")


def show_error(error):
    load_button.config(state="normal")
    status_var.set("Could not load session.")

    messagebox.showerror(
        "Session Loading Error",
        "FastF1 could not load the requested session.\n\n"
        f"{error}\n\n"
        "Check the season, Grand Prix name, session type, "
        "and internet connection."
    )


# search drivers/res
search_frame = ttk.Frame(root, padding=(10, 0, 10, 10))
search_frame.grid(row=3, column=0, sticky="ew")

ttk.Label(search_frame, text="Find in results:").pack(
    side="left", padx=(0, 8)
)

search_var = tk.StringVar()

search_entry = ttk.Entry(
    search_frame,
    textvariable=search_var,
    width=30
)
search_entry.pack(side="left", padx=(0, 8))


def search_results(*args):
    """Filter the results table using the search text."""

    query = search_var.get().strip().casefold()

    for item in results_table.get_children(""):
        values = results_table.item(item, "values")

        matches = (
            not query
            or any(query in str(value).casefold() for value in values)
        )

        if matches:
            results_table.reattach(item, "", "end")
        else:
            results_table.detach(item)


search_var.trace_add("write", search_results)

#buttons
load_button = ttk.Button(
    controls,
    text="Load Session",
    command=load_session
)
load_button.grid(row=0, column=6, padx=10)
root.bind("<Return>", lambda event: load_session())
root.mainloop()