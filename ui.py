import math
import random
import threading
import time
import tkinter as tk
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


class ASICPlacer:
    def __init__(self, design_text, seed=None):
        self.rng = random.Random(seed)
        self.num_components = 0
        self.num_nets = 0
        self.rows = 0
        self.cols = 0
        self.num_pins = 0
        self.num_cells = 0
        self.master_tile = [
            [0, 1, 0, 2, 0],
            [1, 0, 1, 0, 1],
            [0, 2, 3, 0, 2],
            [1, 0, 1, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        self.placement = []
        self.original_pin_placement = []
        self.cell_type = []
        self.cell_ids = []
        self.pin_ids = []
        self.nets = []
        self.component_to_nets = []
        self.legal_sites = [[], [], [], []]
        self.site_to_cell = []
        self.fixed_site = []
        self.affected_mark = []
        self.affected_stamp = 1
        self.net_hpwl = []
        self.history = []
        self.parse_design(design_text)

    def parse_design(self, design_text):
        tokens = design_text.split()
        if len(tokens) < 5:
            raise ValueError("Design text is too short. The first line must contain components, nets, rows, cols, and pins.")

        idx = 0

        def read_token():
            nonlocal idx
            if idx >= len(tokens):
                raise ValueError("Unexpected end of design text.")
            value = tokens[idx]
            idx += 1
            return value

        self.num_components = int(read_token())
        self.num_nets = int(read_token())
        self.rows = int(read_token())
        self.cols = int(read_token())
        self.num_pins = int(read_token())
        self.num_cells = self.num_components - self.num_pins

        self.placement = [(-1, -1) for _ in range(self.num_components)]
        self.original_pin_placement = [(-1, -1) for _ in range(self.num_components)]
        self.cell_type = [-1 for _ in range(self.num_components)]
        self.nets = [[] for _ in range(self.num_nets)]
        self.component_to_nets = [[] for _ in range(self.num_components)]
        self.site_to_cell = [-1 for _ in range(self.rows * self.cols)]
        self.fixed_site = [False for _ in range(self.rows * self.cols)]
        self.affected_mark = [0 for _ in range(self.num_nets)]
        self.net_hpwl = [0 for _ in range(self.num_nets)]
        self.cell_ids = []
        self.pin_ids = []

        for _ in range(self.num_pins):
            pin_id = int(read_token())
            x = int(read_token())
            y = int(read_token())
            read_token()
            self.placement[pin_id] = (x, y)
            self.original_pin_placement[pin_id] = (x, y)
            self.pin_ids.append(pin_id)
            if 0 <= x < self.cols and 0 <= y < self.rows:
                self.fixed_site[self.get_site_index_xy(x, y)] = True

        for _ in range(self.num_cells):
            cell_id = int(read_token())
            type_string = read_token()
            cell_type = int(type_string[1:]) if len(type_string) > 1 else int(type_string)
            self.cell_type[cell_id] = cell_type
            self.cell_ids.append(cell_id)

        for net_id in range(self.num_nets):
            count = int(read_token())
            for _ in range(count):
                component_id = int(read_token())
                self.nets[net_id].append(component_id)
                self.component_to_nets[component_id].append(net_id)

    def get_random_index(self, size):
        return self.rng.randrange(size)

    def get_site_index_xy(self, x, y):
        return y * self.cols + x

    def get_site_index(self, pos):
        return pos[1] * self.cols + pos[0]

    def get_site_type(self, x, y):
        small_x = (x - 1) % 5
        small_y = (y - 1) % 5
        return self.master_tile[small_y][small_x]

    def make_legal_sites(self):
        self.legal_sites = [[], [], [], []]
        for y in range(1, self.rows - 1):
            for x in range(1, self.cols - 1):
                site_type = self.get_site_type(x, y)
                self.legal_sites[site_type].append((x, y))

    def make_initial_placement(self):
        self.site_to_cell = [-1 for _ in range(self.rows * self.cols)]
        available_sites = [sites[:] for sites in self.legal_sites]
        for site_list in available_sites:
            self.rng.shuffle(site_list)
        used_count = [0, 0, 0, 0]
        for cell_id in self.cell_ids:
            ctype = self.cell_type[cell_id]
            if ctype < 0 or ctype > 3 or used_count[ctype] >= len(available_sites[ctype]):
                raise ValueError(f"Not enough legal sites for cell {cell_id}.")
            self.placement[cell_id] = available_sites[ctype][used_count[ctype]]
            self.site_to_cell[self.get_site_index(self.placement[cell_id])] = cell_id
            used_count[ctype] += 1

    def build_site_to_cell(self):
        self.site_to_cell = [-1 for _ in range(self.rows * self.cols)]
        for cell_id in self.cell_ids:
            pos = self.placement[cell_id]
            self.site_to_cell[self.get_site_index(pos)] = cell_id

    def calculate_net_hpwl(self, net_id):
        net = self.nets[net_id]
        first = net[0]
        min_x = self.placement[first][0]
        max_x = min_x
        min_y = self.placement[first][1]
        max_y = min_y
        for component_id in net[1:]:
            x, y = self.placement[component_id]
            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            if y > max_y:
                max_y = y
        return (max_x - min_x) + (max_y - min_y)

    def initialize_net_hpwl(self):
        total = 0
        self.net_hpwl = [0 for _ in range(self.num_nets)]
        for net_id in range(self.num_nets):
            self.net_hpwl[net_id] = self.calculate_net_hpwl(net_id)
            total += self.net_hpwl[net_id]
        return total

    def calculate_total_hpwl(self):
        total = 0
        for net_id in range(self.num_nets):
            total += self.calculate_net_hpwl(net_id)
        return total

    def get_affected_net_ids_fast(self, first_cell, second_cell):
        affected_net_ids = []
        if self.affected_stamp >= 2147483647:
            self.affected_mark = [0 for _ in range(self.num_nets)]
            self.affected_stamp = 1
        else:
            self.affected_stamp += 1

        for net_id in self.component_to_nets[first_cell]:
            if self.affected_mark[net_id] != self.affected_stamp:
                self.affected_mark[net_id] = self.affected_stamp
                affected_net_ids.append(net_id)

        if second_cell != -1:
            for net_id in self.component_to_nets[second_cell]:
                if self.affected_mark[net_id] != self.affected_stamp:
                    self.affected_mark[net_id] = self.affected_stamp
                    affected_net_ids.append(net_id)

        return affected_net_ids

    def apply_move(self, first_cell, old_pos, new_pos, cell_on_site):
        old_index = self.get_site_index(old_pos)
        new_index = self.get_site_index(new_pos)
        self.placement[first_cell] = new_pos
        self.site_to_cell[new_index] = first_cell
        if cell_on_site != -1:
            self.placement[cell_on_site] = old_pos
            self.site_to_cell[old_index] = cell_on_site
        else:
            self.site_to_cell[old_index] = -1

    def undo_move(self, first_cell, old_pos, new_pos, cell_on_site):
        self.apply_move(first_cell, new_pos, old_pos, cell_on_site)

    def pick_move(self):
        first_cell = self.cell_ids[self.get_random_index(len(self.cell_ids))]
        ctype = self.cell_type[first_cell]
        old_pos = self.placement[first_cell]
        for _ in range(100):
            new_pos = self.legal_sites[ctype][self.get_random_index(len(self.legal_sites[ctype]))]
            index = self.get_site_index(new_pos)
            if self.fixed_site[index]:
                continue
            cell_on_site = self.site_to_cell[index]
            return first_cell, old_pos, new_pos, cell_on_site
        return first_cell, old_pos, old_pos, -1

    def run_sa(self, progress_callback=None, should_stop=None):
        current_cost = self.calculate_total_hpwl() if not self.net_hpwl else sum(self.net_hpwl)
        best_cost = current_cost
        best_placement = self.placement[:]
        temperature = 500.0 * current_cost
        final_temperature = (5e-5 * current_cost) / self.num_nets
        step = 0
        self.history = [{"step": step, "temperature": temperature, "current_hpwl": current_cost, "best_hpwl": best_cost}]

        while temperature > final_temperature:
            for iteration in range(20 * self.num_cells):
                if iteration % 1000 == 0 and should_stop is not None and should_stop():
                    raise RuntimeError("Stopped by user.")

                first_cell, old_pos, new_pos, cell_on_site = self.pick_move()

                if new_pos == old_pos:
                    continue

                affected_net_ids = self.get_affected_net_ids_fast(first_cell, cell_on_site)
                old_affected_cost = 0
                for net_id in affected_net_ids:
                    old_affected_cost += self.net_hpwl[net_id]

                self.apply_move(first_cell, old_pos, new_pos, cell_on_site)

                new_affected_cost = 0
                new_net_hpwl_values = []
                for net_id in affected_net_ids:
                    new_hpwl = self.calculate_net_hpwl(net_id)
                    new_net_hpwl_values.append(new_hpwl)
                    new_affected_cost += new_hpwl

                new_cost = current_cost - old_affected_cost + new_affected_cost
                cost_change = new_cost - current_cost
                random_value = self.rng.random()

                if cost_change < 0 or random_value < math.exp(-cost_change / temperature):
                    current_cost = new_cost
                    for i, net_id in enumerate(affected_net_ids):
                        self.net_hpwl[net_id] = new_net_hpwl_values[i]
                    if current_cost < best_cost:
                        best_cost = current_cost
                        best_placement = self.placement[:]
                else:
                    self.undo_move(first_cell, old_pos, new_pos, cell_on_site)

            temperature *= 0.95
            step += 1
            point = {"step": step, "temperature": temperature, "current_hpwl": current_cost, "best_hpwl": best_cost}
            self.history.append(point)
            if progress_callback is not None and (step % 5 == 0 or temperature <= final_temperature):
                progress_callback(point)

        self.placement = best_placement[:]
        self.build_site_to_cell()
        return best_cost

    def verify_placement(self):
        seen = [-1 for _ in range(self.rows * self.cols)]
        for pin_id in self.pin_ids:
            pos = self.placement[pin_id]
            if pos != self.original_pin_placement[pin_id]:
                return False, f"ERROR: Pin {pin_id} moved"
            x, y = pos
            if 0 <= x < self.cols and 0 <= y < self.rows:
                seen[self.get_site_index(pos)] = pin_id

        for cell_id in self.cell_ids:
            pos = self.placement[cell_id]
            x, y = pos
            if x <= 0 or x >= self.cols - 1 or y <= 0 or y >= self.rows - 1:
                return False, f"ERROR: Cell {cell_id} is outside legal area"
            index = self.get_site_index(pos)
            if seen[index] != -1:
                return False, f"ERROR: Cell {cell_id} overlaps with component {seen[index]}"
            seen[index] = cell_id
            actual_type = self.get_site_type(x, y)
            if actual_type != self.cell_type[cell_id]:
                return False, f"ERROR: Cell {cell_id} is on wrong site type"

        return True, "Placement is VALID"

    def get_components_for_ui(self):
        components = []
        for pin_id in self.pin_ids:
            x, y = self.placement[pin_id]
            components.append({"id": pin_id, "x": x, "y": y, "kind": "pin", "type": -1})
        for cell_id in self.cell_ids:
            x, y = self.placement[cell_id]
            components.append({"id": cell_id, "x": x, "y": y, "kind": "cell", "type": self.cell_type[cell_id]})
        return components


class PlacementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Self-Contained DD2 SA Placement UI")
        self.root.geometry("1450x900")
        self.root.minsize(1150, 720)

        self.status = tk.StringVar(value="Ready")
        self.initial_hpwl = tk.StringVar(value="-")
        self.final_hpwl = tk.StringVar(value="-")
        self.improvement = tk.StringVar(value="-")
        self.validity = tk.StringVar(value="-")
        self.sa_time = tk.StringVar(value="-")
        self.seed_value = tk.StringVar(value="")
        self.title_text = tk.StringVar(value="No placement loaded")

        self.placer = None
        self.components = []
        self.history = []
        self.rows = 0
        self.cols = 0
        self.num_components = 0
        self.num_nets = 0
        self.num_pins = 0
        self.running_thread = None
        self.stop_requested = False

        self.build_ui()

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main = ttk.Frame(self.root, padding=10)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        header = ttk.LabelFrame(main, text="Self-contained input", padding=10)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(8, weight=1)

        ttk.Button(header, text="Load design text", command=self.load_design_text).grid(row=0, column=0, padx=4, pady=3)
        ttk.Button(header, text="Run SA in UI", command=self.run_sa_from_ui).grid(row=0, column=1, padx=4, pady=3)
        ttk.Button(header, text="Stop", command=self.stop_run).grid(row=0, column=2, padx=4, pady=3)
        ttk.Button(header, text="Redraw", command=self.redraw_all).grid(row=0, column=3, padx=4, pady=3)
        ttk.Button(header, text="Clear output", command=self.clear_output).grid(row=0, column=4, padx=4, pady=3)
        ttk.Button(header, text="Clear input", command=self.clear_input).grid(row=0, column=5, padx=4, pady=3)
        ttk.Label(header, text="Seed:").grid(row=0, column=6, padx=(18, 4), sticky="e")
        ttk.Entry(header, textvariable=self.seed_value, width=12).grid(row=0, column=7, padx=4, sticky="w")
        ttk.Label(header, textvariable=self.status).grid(row=0, column=8, padx=(20, 0), sticky="w")

        summary = ttk.LabelFrame(main, text="Summary", padding=10)
        summary.grid(row=1, column=0, sticky="ew", pady=8)
        summary.columnconfigure(13, weight=1)

        pairs = [
            ("Initial HPWL", self.initial_hpwl),
            ("Final HPWL", self.final_hpwl),
            ("Improvement", self.improvement),
            ("SA Time", self.sa_time),
            ("Validity", self.validity),
        ]
        for i, (label, variable) in enumerate(pairs):
            ttk.Label(summary, text=f"{label}:").grid(row=0, column=i * 2, sticky="w", padx=(0, 4))
            ttk.Label(summary, textvariable=variable).grid(row=0, column=i * 2 + 1, sticky="w", padx=(0, 18))

        info = ttk.LabelFrame(main, text="What this version does", padding=10)
        info.grid(row=2, column=0, sticky="ew")
        ttk.Label(info, text="Paste the design text or load it into the box below, then press Run SA in UI. No C++ compile, no single_placer, no results folder, no CSV files.").grid(row=0, column=0, sticky="w")

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
        input_frame = ttk.Frame(notebook)
        notebook.add(placement_frame, text="Placement Visualization")
        notebook.add(hpwl_frame, text="HPWL Plot")
        notebook.add(input_frame, text="Design Input")

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

        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)
        self.input_text = tk.Text(input_frame, wrap="none", font=("Consolas", 10))
        self.input_text.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        input_y = ttk.Scrollbar(input_frame, orient="vertical", command=self.input_text.yview)
        input_y.grid(row=0, column=1, sticky="ns", pady=8)
        input_x = ttk.Scrollbar(input_frame, orient="horizontal", command=self.input_text.xview)
        input_x.grid(row=1, column=0, sticky="ew", padx=(8, 0))
        self.input_text.configure(yscrollcommand=input_y.set, xscrollcommand=input_x.set)

        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        output_box = ttk.LabelFrame(right, text="Output", padding=8)
        output_box.grid(row=0, column=0, sticky="nsew")
        output_box.columnconfigure(0, weight=1)
        output_box.rowconfigure(0, weight=1)

        self.output = tk.Text(output_box, wrap="word", font=("Consolas", 10))
        self.output.grid(row=0, column=0, sticky="nsew")
        output_scrollbar = ttk.Scrollbar(output_box, command=self.output.yview)
        output_scrollbar.grid(row=0, column=1, sticky="ns")
        self.output.configure(yscrollcommand=output_scrollbar.set)

    def load_design_text(self):
        path = filedialog.askopenfilename(filetypes=[("Design text files", "*.txt"), ("All files", "*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as file:
                text = file.read()
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", text)
            self.append_output(f"Loaded design text into UI: {path}\n")
            self.status.set("Design loaded into memory")
        except Exception as exc:
            messagebox.showerror("Load error", str(exc))

    def clear_input(self):
        self.input_text.delete("1.0", "end")
        self.status.set("Input cleared")

    def clear_output(self):
        self.output.delete("1.0", "end")
        self.status.set("Ready")

    def append_output(self, text):
        self.output.insert("end", text)
        self.output.see("end")

    def run_sa_from_ui(self):
        if self.running_thread is not None and self.running_thread.is_alive():
            messagebox.showwarning("Already running", "SA is already running.")
            return

        design_text = self.input_text.get("1.0", "end").strip()
        if not design_text:
            messagebox.showwarning("Missing input", "Paste the design text in the Design Input tab or load a design text file into the UI.")
            return

        seed_text = self.seed_value.get().strip()
        seed = None
        if seed_text:
            try:
                seed = int(seed_text)
            except ValueError:
                messagebox.showerror("Invalid seed", "Seed must be an integer or empty.")
                return

        self.stop_requested = False
        self.status.set("Running SA inside UI")
        self.initial_hpwl.set("-")
        self.final_hpwl.set("-")
        self.improvement.set("-")
        self.validity.set("-")
        self.sa_time.set("-")
        self.append_output("\nRunning self-contained SA logic...\n")

        self.running_thread = threading.Thread(target=self.worker_run_sa, args=(design_text, seed), daemon=True)
        self.running_thread.start()

    def stop_run(self):
        self.stop_requested = True
        self.status.set("Stopping after current batch")

    def worker_run_sa(self, design_text, seed):
        try:
            placer = ASICPlacer(design_text, seed=seed)
            placer.make_legal_sites()
            placer.make_initial_placement()
            placer.build_site_to_cell()
            initial_hpwl = placer.initialize_net_hpwl()
            start_time = time.perf_counter()

            def progress(point):
                self.root.after(0, self.status.set, f"Running | step {point['step']} | best {point['best_hpwl']}")

            best_cost = placer.run_sa(progress_callback=progress, should_stop=lambda: self.stop_requested)
            elapsed = time.perf_counter() - start_time
            valid, validity_message = placer.verify_placement()
            final_components = placer.get_components_for_ui()
            history = placer.history[:]
            self.root.after(0, self.finish_success, placer, initial_hpwl, best_cost, elapsed, valid, validity_message, final_components, history)
        except Exception as exc:
            self.root.after(0, self.finish_error, exc)

    def finish_success(self, placer, initial_hpwl, best_cost, elapsed, valid, validity_message, final_components, history):
        self.placer = placer
        self.components = final_components
        self.history = history
        self.rows = placer.rows
        self.cols = placer.cols
        self.num_components = placer.num_components
        self.num_nets = placer.num_nets
        self.num_pins = placer.num_pins

        self.initial_hpwl.set(str(initial_hpwl))
        self.final_hpwl.set(str(best_cost))
        if initial_hpwl > 0:
            improvement = 100.0 * (initial_hpwl - best_cost) / initial_hpwl
            self.improvement.set(f"{improvement:.2f}%")
        else:
            self.improvement.set("-")
        self.sa_time.set(f"{elapsed:.4f} s")
        self.validity.set("VALID" if valid else "INVALID")
        self.status.set("Finished" if valid else "Finished with invalid placement")

        self.append_output(f"Initial total HPWL: {initial_hpwl}\n")
        self.append_output(f"Final best HPWL: {best_cost}\n")
        self.append_output(f"SA runtime only: {elapsed:.6f} seconds\n")
        self.append_output(validity_message + "\n")
        self.redraw_all()

    def finish_error(self, exc):
        self.status.set("Error")
        self.append_output(f"ERROR: {exc}\n")
        messagebox.showerror("Run error", str(exc))

    def redraw_all(self):
        self.draw_placement()
        self.draw_hpwl()

    def make_title(self):
        initial = self.initial_hpwl.get()
        final = self.final_hpwl.get()
        improvement = self.improvement.get()
        if initial != "-" and final != "-":
            return f"Final placement | HPWL {initial} -> {final} | improvement {improvement}"
        return "Final placement"

    def draw_placement(self):
        canvas = self.placement_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 800)
        height = max(canvas.winfo_height(), 550)

        if self.rows <= 0 or self.cols <= 0:
            canvas.create_text(width / 2, height / 2, text="No placement loaded yet", fill=COLORS["text"], font=("TkDefaultFont", 16, "bold"))
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

        self.title_text.set(self.make_title())
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
            fill = COLORS["pin"] if item["kind"] == "pin" else COLORS.get(item["type"], "#777777")
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
            canvas.create_text(width / 2, height / 2, text="No HPWL history yet", fill=COLORS["text"], font=("TkDefaultFont", 16, "bold"))
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

        canvas.create_text(left + plot_w / 2, height - 22, text="Cooling step", font=("TkDefaultFont", 12), fill=COLORS["text"])
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
