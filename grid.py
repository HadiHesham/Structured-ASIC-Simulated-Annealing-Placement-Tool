import random

MASTER_TILE = [
    ["T0", "T1", "T0", "T2", "T0"],
    ["T1", "T0", "T1", "T0", "T1"],
    ["T0", "T2", "T3", "T0", "T2"],
    ["T1", "T0", "T1", "T0", "T0"],
    ["T0", "T0", "T0", "T0", "T0"],
]

def get_site_type(x, y):
    # Given a core position (x, y), return what type of site it is
    # We use (y-1) and (x-1) because the core starts at index 1, not 0
    row = (y - 1) % 5
    col = (x - 1) % 5
    return MASTER_TILE[row][col]

def build_grid(rows, cols):
    # Create a rows x cols grid
    # Each cell in the grid is a dictionary holding:
    #   - "site_type": what type this site accepts (T0/T1/T2/T3 or "PIN" or "PERIMETER")
    #   - "occupant": who is currently placed here (None if empty)

    grid = []
    for y in range(rows):
        row_list = []
        for x in range(cols):
            # Check if this position is on the perimeter
            is_perimeter = (x == 0 or x == cols - 1 or y == 0 or y == rows - 1)

            if is_perimeter:
                site = {"site_type": "PIN", "occupant": None}
            else:
                # Core site — figure out its type from the master tile
                site = {"site_type": get_site_type(x, y), "occupant": None}

            row_list.append(site)
        grid.append(row_list)

    return grid

def place_pins(grid, pins):
    # Fix all pins onto the perimeter — they never move
    for pin_id, coords in pins.items():
        x, y = coords
        grid[y][x]["occupant"] = ("PIN", pin_id)

def get_empty_sites_by_type(grid, rows, cols):
    # Build a dictionary mapping each type to a list of empty core sites
    # This makes initial placement fast — we just pick from the right list
    empty_sites = {"T0": [], "T1": [], "T2": [], "T3": []}

    for y in range(1, rows - 1):       # skip perimeter rows
        for x in range(1, cols - 1):   # skip perimeter cols
            site = grid[y][x]
            if site["occupant"] is None:
                empty_sites[site["site_type"]].append((x, y))

    return empty_sites

def initial_placement(grid, cells, rows, cols):
    # Randomly place each movable cell on an empty site of matching type
    empty_sites = get_empty_sites_by_type(grid, rows, cols)

    # Shuffle each list so placement is random
    for site_type in empty_sites:
        random.shuffle(empty_sites[site_type])

    # Track where each cell ends up: cell_id -> (x, y)
    cell_positions = {}

    for cell_id, cell_type in cells.items():
        if len(empty_sites[cell_type]) == 0:
            print(f"ERROR: No empty {cell_type} site available for cell {cell_id}")
            return None, None

        # Pop a random site of the correct type
        x, y = empty_sites[cell_type].pop()

        # Place the cell on the grid
        grid[y][x]["occupant"] = ("CELL", cell_id)

        # Remember where this cell is
        cell_positions[cell_id] = (x, y)

    return grid, cell_positions

def main():
    # Import the parser
    from parser_step1 import read_file, read_header, read_pins, read_cells, read_nets

    # Parse the input file
    lines = read_file("design_1_small.txt")
    num_components, num_nets, rows, cols, num_pins = read_header(lines[0])
    pins, next_line = read_pins(lines, 1, num_pins)
    num_cells = num_components - num_pins
    cells, next_line = read_cells(lines, next_line, num_cells)

    # Build the grid
    grid = build_grid(rows, cols)
    print("Grid built successfully")

    # Place pins (fixed)
    place_pins(grid, pins)
    print("Pins placed on perimeter")

    # Place movable cells randomly
    grid, cell_positions = initial_placement(grid, cells, rows, cols)
    print("Initial placement done")

    # Quick sanity check — print a few cell positions
    for cell_id in list(cell_positions.keys())[:5]:
        x, y = cell_positions[cell_id]
        cell_type = cells[cell_id]
        site_type = grid[y][x]["site_type"]
        print(f"Cell {cell_id} ({cell_type}) placed at ({x},{y}) — site type: {site_type}")

if __name__ == "__main__":
    main()
