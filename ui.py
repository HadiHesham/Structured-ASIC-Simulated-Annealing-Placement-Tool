import csv
import os
import re
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


COLORS = {
    "pin": "#111111",
    0: "#4e79a7",
    1: "#59a14f",
    2: "#f28e2b",
    3: "#e15759",
    "empty": "#f3f3f3",
    "minor": "#d2d2d2",
    "major": "#444444",
    "text": "#222222",
    "current": "#b7aea9",
    "best": "#4e79a7",
}


class PlacementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DD2 Structured ASIC Placement Viewer")
        self.root.geometry("1400x850")
        self.root.minsize(1100, 700)

        self.project_dir = Path(__file__).resolve().parent
        self.input_path = tk.StringVar(value="design_5_extreme.txt")
        self.output_dir = tk.StringVar(value="results")
        self.status = tk.StringVar(value="Ready")
        self.initial_hpwl = tk.StringVar(value="-")
        self.final_hpwl = tk.StringVar(value="-")
        self.improvement = tk.StringVar(value="-")
        self.validity = tk.StringVar(value="-")
        self.title_text = tk.StringVar(value="No placement loaded")
        self.process = None
        self.rows = 0
        self.cols = 0
        self.num_components = 0
        self.num_nets = 0
        self.num_pins = 0
        self.components = []
        self.history = []
        self.build_ui()
        self.root.after(200, self.load_results_silent)

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main = ttk.Frame(self.root, padding=10)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        header = ttk.LabelFrame(main, text="Input and Output", padding=10)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        header.columnconfigure(4, weight=1)

        ttk.Label(header, text="Design file:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Entry(header, textvariable=self.input_path).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(header, text="Browse", command=self.pick_input).grid(row=0, column=2, sticky="ew", padx=(0, 14))
        ttk.Label(header, text="Output folder:").grid(row=0, column=3, sticky="w", padx=(0, 6))
        ttk.Entry(header, textvariable=self.output_dir).grid(row=0, column=4, sticky="ew", padx=(0, 6))
        ttk.Button(header, text="Open", command=self.open_output_folder).grid(row=0, column=5, sticky="ew")

        controls = ttk.LabelFrame(main, text="Controls", padding=10)
        controls.grid(row=1, column=0, sticky="ew", pady=8)

        ttk.Button(controls, text="Compile", command=self.compile_cpp).grid(row=0, column=0, padx=4, pady=3)
        ttk.Button(controls, text="Run SA", command=self.run_cpp).grid(row=0, column=1, padx=4, pady=3)
        ttk.Button(controls, text="Compile + Run", command=self.compile_and_run).grid(row=0, column=2, padx=4, pady=3)
        ttk.Button(controls, text="Load Placement", command=self.load_results).grid(row=0, column=3, padx=4, pady=3)
        ttk.Button(controls, text="Redraw", command=self.redraw_all).grid(row=0, column=4, padx=4, pady=3)
        ttk.Button(controls, text="Clear Output", command=self.clear_output).grid(row=0, column=5, padx=4, pady=3)

        summary = ttk.LabelFrame(main, text="Summary", padding=10)
        summary.grid(row=2, column=0, sticky="ew")
        summary.columnconfigure(9, weight=1)

        pairs = [
            ("Initial HPWL", self.initial_hpwl),
            ("Final HPWL", self.final_hpwl),
            ("Improvement", self.improvement),
            ("Validity", self.validity),
            ("Status", self.status),
        ]
        for i, (label, variable) in enumerate(pairs):
            ttk.Label(summary, text=f"{label}:").grid(row=0, column=i * 2, sticky="w", padx=(0, 4))
            ttk.Label(summary, textvariable=variable).grid(row=0, column=i * 2 + 1, sticky="w", padx=(0, 18))

        body = ttk.PanedWindow(main, orient="horizontal")
        body.grid(row=3, column=0, sticky="nsew", pady=(8, 0))

        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=4)
        body.add(right, weight=2)

        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(left)
        notebook.grid(row=0, column=0, sticky="nsew")

        placement_frame = ttk.Frame(notebook)
        hpwl_frame = ttk.Frame(notebook)
        notebook.add(placement_frame, text="Placement Visualization")
        notebook.add(hpwl_frame, text="HPWL Plot")

        placement_frame.columnconfigure(0, weight=1)
        placement_frame.rowconfigure(1, weight=1)
        ttk.Label(placement_frame, textvariable=self.title_text, font=("TkDefaultFont", 14, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.placement_canvas = tk.Canvas(placement_frame, bg="white", highlightthickness=1, highlightbackground="#c0c0c0")
        self.placement_canvas.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.placement_canvas.bind("<Configure>", lambda event: self.draw_placement())

        hpwl_frame.columnconfigure(0, weight=1)
        hpwl_frame.rowconfigure(0, weight=1)
        self.hpwl_canvas = tk.Canvas(hpwl_frame, bg="white", highlightthickness=1, highlightbackground="#c0c0c0")
        self.hpwl_canvas.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.hpwl_canvas.bind("<Configure>", lambda event: self.draw_hpwl())

        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        output_box = ttk.LabelFrame(right, text="Program Output", padding=8)
        output_box.grid(row=0, column=0, sticky="nsew")
        output_box.columnconfigure(0, weight=1)
        output_box.rowconfigure(0, weight=1)

        self.output = tk.Text(output_box, wrap="word", font=("Consolas", 10))
        self.output.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(output_box, command=self.output.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.output.configure(yscrollcommand=scrollbar.set)

    def pick_input(self):
        path = filedialog.askopenfilename(initialdir=self.project_dir, filetypes=[("Design text files", "*.txt"), ("All files", "*")])
        if not path:
            return
        try:
            self.input_path.set(str(Path(path).resolve().relative_to(self.project_dir)))
        except ValueError:
            self.input_path.set(str(Path(path).resolve()))

    def open_output_folder(self):
        folder = self.project_dir / self.output_dir.get()
        folder.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(folder))
        else:
            subprocess.Popen(["xdg-open", str(folder)])

    def append_output(self, text):
        self.output.insert("end", text)
        self.output.see("end")

    def clear_output(self):
        self.output.delete("1.0", "end")
        self.status.set("Ready")

    def compile_cpp(self):
        self.run_command(["g++", "-std=c++17", "-O3", "-march=native", "-DNDEBUG", "main.cpp", "-o", "single_placer"], after=None)

    def run_cpp(self):
        self.run_command(["./single_placer", self.input_path.get(), self.output_dir.get()], after=self.load_results_silent)

    def compile_and_run(self):
        def after_compile(code):
            if code == 0:
                self.run_cpp()
        self.run_command(["g++", "-std=c++17", "-O3", "-march=native", "-DNDEBUG", "main.cpp", "-o", "single_placer"], after=after_compile)

    def run_command(self, args, after=None):
        if self.process is not None:
            messagebox.showwarning("Already running", "A process is already running.")
            return
        self.status.set("Running")
        self.append_output("\n$ " + " ".join(args) + "\n")
        thread = threading.Thread(target=self.worker, args=(args, after), daemon=True)
        thread.start()

    def worker(self, args, after):
        code = -1
        try:
            self.process = subprocess.Popen(args, cwd=self.project_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in self.process.stdout:
                self.root.after(0, self.append_output, line)
            code = self.process.wait()
            self.root.after(0, self.status.set, "Finished" if code == 0 else f"Failed {code}")
        except Exception as exc:
            self.root.after(0, self.append_output, f"ERROR: {exc}\n")
            self.root.after(0, self.status.set, "Error")
        finally:
            self.process = None
            self.root.after(0, self.parse_terminal_summary)
            if after is not None:
                self.root.after(0, lambda: after(code) if callable(after) and after.__name__ != "load_results_silent" else after())

    def parse_design_header(self):
        path = Path(self.input_path.get())
        if not path.is_absolute():
            path = self.project_dir / path
        if not path.exists():
            return False
        tokens = path.read_text(errors="ignore").split()
        if len(tokens) < 5:
            return False
        try:
            self.num_components = int(tokens[0])
            self.num_nets = int(tokens[1])
            self.rows = int(tokens[2])
            self.cols = int(tokens[3])
            self.num_pins = int(tokens[4])
            return True
        except ValueError:
            return False

    def output_path(self, name):
        return self.project_dir / self.output_dir.get() / name

    def load_results_silent(self):
        try:
            self.load_results(show_errors=False)
        except Exception:
            pass

    def load_results(self, show_errors=True):
        placement_path = self.output_path("final_placement.csv")
        history_path = self.output_path("hpwl_history.csv")
        summary_path = self.output_path("summary.txt")

        if not self.parse_design_header():
            self.try_parse_summary(summary_path)

        if not placement_path.exists():
            if show_errors:
                messagebox.showinfo("Missing placement", f"Run the C++ program first. Expected file:\n{placement_path}")
            self.draw_placement()
            return

        self.components = []
        with placement_path.open(newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                kind = row.get("component_kind", "cell").strip()
                type_value = row.get("type", "-1").strip()
                item = {
                    "id": int(row["component_id"]),
                    "x": int(row["x"]),
                    "y": int(row["y"]),
                    "kind": kind,
                    "type": int(type_value) if type_value not in ["", "-1"] else -1,
                }
                self.components.append(item)

        self.history = []
        if history_path.exists():
            with history_path.open(newline="") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    self.history.append({
                        "step": int(row["step"]),
                        "temperature": float(row["temperature"]),
                        "current_hpwl": int(row["current_hpwl"]),
                        "best_hpwl": int(row["best_hpwl"]),
                    })

        self.try_parse_summary(summary_path)
        self.redraw_all()

    def try_parse_summary(self, path):
        if not path.exists():
            return
        text = path.read_text(errors="ignore")
        values = {
            "Initial total HPWL": self.initial_hpwl,
            "Final best HPWL": self.final_hpwl,
            "Improvement percent": self.improvement,
            "Placement validity": self.validity,
        }
        for key, variable in values.items():
            match = re.search(rf"{re.escape(key)}:\s*([^\n]+)", text)
            if match:
                value = match.group(1).strip()
                if key == "Improvement percent" and not value.endswith("%"):
                    value += "%"
                variable.set(value)
        rows_match = re.search(r"Rows:\s*(\d+)", text)
        cols_match = re.search(r"Cols:\s*(\d+)", text)
        comp_match = re.search(r"Components:\s*(\d+)", text)
        net_match = re.search(r"Nets:\s*(\d+)", text)
        pins_match = re.search(r"Pins:\s*(\d+)", text)
        if rows_match:
            self.rows = int(rows_match.group(1))
        if cols_match:
            self.cols = int(cols_match.group(1))
        if comp_match:
            self.num_components = int(comp_match.group(1))
        if net_match:
            self.num_nets = int(net_match.group(1))
        if pins_match:
            self.num_pins = int(pins_match.group(1))

    def parse_terminal_summary(self):
        text = self.output.get("1.0", "end")
        initial = re.findall(r"Initial total HPWL:\s*(\d+)", text)
        final = re.findall(r"Final best HPWL:\s*(\d+)", text)
        valid = re.findall(r"Placement is VALID", text)
        if initial:
            self.initial_hpwl.set(initial[-1])
        if final:
            self.final_hpwl.set(final[-1])
        if initial and final and int(initial[-1]) > 0:
            value = 100.0 * (int(initial[-1]) - int(final[-1])) / int(initial[-1])
            self.improvement.set(f"{value:.2f}%")
        if valid:
            self.validity.set("VALID")

    def redraw_all(self):
        self.draw_placement()
        self.draw_hpwl()

    def draw_placement(self):
        canvas = self.placement_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 800)
        height = max(canvas.winfo_height(), 550)

        if self.rows <= 0 or self.cols <= 0:
            canvas.create_text(width / 2, height / 2, text="No design loaded yet", fill=COLORS["text"], font=("TkDefaultFont", 16, "bold"))
            return

        legend_width = 170
        left = 52
        top = 42
        right_padding = 28
        bottom_padding = 42
        board_w = width - left - legend_width - right_padding
        board_h = height - top - bottom_padding
        cell = max(4, min(board_w / self.cols, board_h / self.rows))
        grid_w = self.cols * cell
        grid_h = self.rows * cell

        title = self.make_title()
        self.title_text.set(title)

        canvas.create_rectangle(left, top, left + grid_w, top + grid_h, fill=COLORS["empty"], outline="")

        for item in self.components:
            x = item["x"]
            y = item["y"]
            if x < 0 or y < 0 or x >= self.cols or y >= self.rows:
                continue
            x0 = left + x * cell
            y0 = top + y * cell
            x1 = x0 + cell
            y1 = y0 + cell
            if item["kind"] == "pin":
                fill = COLORS["pin"]
            else:
                fill = COLORS.get(item["type"], "#777777")
            canvas.create_rectangle(x0 + 0.5, y0 + 0.5, x1 - 0.5, y1 - 0.5, fill=fill, outline=fill)

        for x in range(self.cols + 1):
            xpos = left + x * cell
            if x % 5 == 0:
                canvas.create_line(xpos, top, xpos, top + grid_h, fill=COLORS["major"], width=2)
            else:
                canvas.create_line(xpos, top, xpos, top + grid_h, fill=COLORS["minor"], width=1)

        for y in range(self.rows + 1):
            ypos = top + y * cell
            if y % 5 == 0:
                canvas.create_line(left, ypos, left + grid_w, ypos, fill=COLORS["major"], width=2)
            else:
                canvas.create_line(left, ypos, left + grid_w, ypos, fill=COLORS["minor"], width=1)

        canvas.create_rectangle(left, top, left + grid_w, top + grid_h, outline=COLORS["major"], width=2)

        label_step = 5 if self.cols <= 80 else 10
        for x in range(0, self.cols + 1, label_step):
            xpos = left + x * cell
            canvas.create_text(xpos, top - 14, text=str(x), fill="#555555", font=("TkDefaultFont", 9))
        for y in range(0, self.rows + 1, label_step):
            ypos = top + y * cell
            canvas.create_text(left - 18, ypos, text=str(y), fill="#555555", font=("TkDefaultFont", 9))

        self.draw_legend(canvas, left + grid_w + 35, top)

    def make_title(self):
        design_name = Path(self.input_path.get()).name
        initial = self.initial_hpwl.get()
        final = self.final_hpwl.get()
        improvement = self.improvement.get()
        if initial != "-" and final != "-":
            return f"{design_name}: final placement | HPWL {initial} -> {final} | improvement {improvement}"
        return f"{design_name}: final placement"

    def draw_legend(self, canvas, x, y):
        canvas.create_text(x, y, text="Legend", anchor="nw", font=("TkDefaultFont", 15, "bold"), fill=COLORS["text"])
        entries = [
            ("Pin", COLORS["pin"]),
            ("Type 0", COLORS[0]),
            ("Type 1", COLORS[1]),
            ("Type 2", COLORS[2]),
            ("Type 3", COLORS[3]),
            ("Empty", COLORS["empty"]),
        ]
        start_y = y + 42
        for i, (name, color) in enumerate(entries):
            yy = start_y + i * 34
            canvas.create_rectangle(x, yy, x + 22, yy + 22, fill=color, outline="#aaaaaa")
            canvas.create_text(x + 34, yy + 11, text=name, anchor="w", font=("TkDefaultFont", 12), fill=COLORS["text"])

        counts = {"pin": 0, 0: 0, 1: 0, 2: 0, 3: 0}
        for item in self.components:
            if item["kind"] == "pin":
                counts["pin"] += 1
            else:
                counts[item["type"]] = counts.get(item["type"], 0) + 1
        yy = start_y + len(entries) * 34 + 20
        canvas.create_text(x, yy, text="Counts", anchor="nw", font=("TkDefaultFont", 13, "bold"), fill=COLORS["text"])
        lines = [
            f"Pins: {counts['pin']}",
            f"Type 0: {counts.get(0, 0)}",
            f"Type 1: {counts.get(1, 0)}",
            f"Type 2: {counts.get(2, 0)}",
            f"Type 3: {counts.get(3, 0)}",
        ]
        for i, line in enumerate(lines):
            canvas.create_text(x, yy + 28 + i * 22, text=line, anchor="nw", font=("TkDefaultFont", 10), fill="#555555")

    def draw_hpwl(self):
        canvas = self.hpwl_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 800)
        height = max(canvas.winfo_height(), 500)

        if not self.history:
            canvas.create_text(width / 2, height / 2, text="No HPWL history loaded yet", fill=COLORS["text"], font=("TkDefaultFont", 16, "bold"))
            return

        left = 75
        right = 40
        top = 55
        bottom = 65
        plot_w = width - left - right
        plot_h = height - top - bottom

        steps = [p["step"] for p in self.history]
        current = [p["current_hpwl"] for p in self.history]
        best = [p["best_hpwl"] for p in self.history]
        all_values = current + best
        x_min = min(steps)
        x_max = max(steps) if max(steps) > x_min else x_min + 1
        y_min = min(all_values)
        y_max = max(all_values) if max(all_values) > y_min else y_min + 1
        padding = max(1, int((y_max - y_min) * 0.08))
        y_min -= padding
        y_max += padding

        def sx(value):
            return left + (value - x_min) * plot_w / (x_max - x_min)

        def sy(value):
            return top + (y_max - value) * plot_h / (y_max - y_min)

        canvas.create_text(left, 22, text="HPWL over annealing steps", anchor="w", font=("TkDefaultFont", 18, "bold"), fill=COLORS["text"])
        canvas.create_rectangle(left, top, left + plot_w, top + plot_h, outline="#cccccc", fill="white")

        for i in range(6):
            y_value = y_min + i * (y_max - y_min) / 5
            y_pos = sy(y_value)
            canvas.create_line(left, y_pos, left + plot_w, y_pos, fill="#eeeeee")
            canvas.create_text(left - 10, y_pos, text=str(int(y_value)), anchor="e", fill="#555555", font=("TkDefaultFont", 9))

        for i in range(6):
            x_value = x_min + i * (x_max - x_min) / 5
            x_pos = sx(x_value)
            canvas.create_line(x_pos, top, x_pos, top + plot_h, fill="#f1f1f1")
            canvas.create_text(x_pos, top + plot_h + 20, text=str(int(x_value)), anchor="n", fill="#555555", font=("TkDefaultFont", 9))

        self.draw_line(canvas, steps, current, sx, sy, COLORS["current"], 2)
        self.draw_line(canvas, steps, best, sx, sy, COLORS["best"], 3)

        canvas.create_text(left + plot_w / 2, height - 22, text="Temperature step", font=("TkDefaultFont", 12), fill=COLORS["text"])
        canvas.create_text(24, top + plot_h / 2, text="HPWL", angle=90, font=("TkDefaultFont", 12), fill=COLORS["text"])

        legend_x = left + plot_w - 220
        legend_y = top + 15
        canvas.create_line(legend_x, legend_y, legend_x + 70, legend_y, fill=COLORS["current"], width=3)
        canvas.create_text(legend_x + 82, legend_y, text="Current HPWL", anchor="w", font=("TkDefaultFont", 11), fill="#7a716c")
        canvas.create_line(legend_x, legend_y + 28, legend_x + 70, legend_y + 28, fill=COLORS["best"], width=3)
        canvas.create_text(legend_x + 82, legend_y + 28, text="Best-so-far HPWL", anchor="w", font=("TkDefaultFont", 11), fill=COLORS["best"])

    def draw_line(self, canvas, xs, ys, sx, sy, color, width):
        if len(xs) < 2:
            return
        points = []
        for x, y in zip(xs, ys):
            points.extend([sx(x), sy(y)])
        canvas.create_line(*points, fill=color, width=width, smooth=False)


def main():
    root = tk.Tk()
    PlacementApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
