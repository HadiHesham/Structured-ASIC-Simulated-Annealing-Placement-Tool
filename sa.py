import math
import random

# ─────────────────────────────────────────
# HPWL: Half Perimeter Wire Length
# For each net, find the bounding box of all
# its components and return half the perimeter
# ─────────────────────────────────────────
def compute_hpwl_one_net(net, cell_positions, pins):
    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')

    for component_id in net:
        if component_id in pins:
            x, y = pins[component_id]
        elif component_id in cell_positions:
            x, y = cell_positions[component_id]
        else:
            continue

        if x < min_x: min_x = x
        if x > max_x: max_x = x
        if y < min_y: min_y = y
        if y > max_y: max_y = y

    # If only one component, wire length is 0
    if min_x == float('inf'):
        return 0

    return (max_x - min_x) + (max_y - min_y)

def compute_total_hpwl(nets, cell_positions, pins):
    total = 0
    for net in nets:
        total += compute_hpwl_one_net(net, cell_positions, pins)
    return total

# ─────────────────────────────────────────
# Find which nets a cell belongs to
# We precompute this once so SA is fast
# ─────────────────────────────────────────
def build_cell_to_nets(nets, num_components):
    cell_to_nets = {}
    for i in range(num_components):
        cell_to_nets[i] = []

    for net_index, net in enumerate(nets):
        for component_id in net:
            if component_id in cell_to_nets:
                cell_to_nets[component_id].append(net_index)

    return cell_to_nets

# ─────────────────────────────────────────
# Compute cost change for ONE swap
# Only recalculate nets affected by the swap
# (much faster than recalculating everything)
# ─────────────────────────────────────────
def compute_delta_cost(cell_a, cell_b, cell_positions, pins, nets, cell_to_nets):
    # Find all nets affected by either cell_a or cell_b
    affected_nets = set()
    if cell_a in cell_to_nets:
        for net_idx in cell_to_nets[cell_a]:
            affected_nets.add(net_idx)
    if cell_b is not None and cell_b in cell_to_nets:
        for net_idx in cell_to_nets[cell_b]:
            affected_nets.add(net_idx)

    # Calculate cost BEFORE the swap
    cost_before = 0
    for net_idx in affected_nets:
        cost_before += compute_hpwl_one_net(nets[net_idx], cell_positions, pins)

    # Do the swap
    pos_a = cell_positions[cell_a]
    if cell_b is not None:
        pos_b = cell_positions[cell_b]
        cell_positions[cell_a] = pos_b
        cell_positions[cell_b] = pos_a
    else:
        # Swapping with empty site — cell_b is None, pos_b is the empty position
        # We handle this differently (see run_sa)
        pass

    # Calculate cost AFTER the swap
    cost_after = 0
    for net_idx in affected_nets:
        cost_after += compute_hpwl_one_net(nets[net_idx], cell_positions, pins)

    # Undo the swap (we'll officially apply it only if accepted)
    if cell_b is not None:
        cell_positions[cell_a] = pos_a
        cell_positions[cell_b] = pos_b

    return cost_after - cost_before

# ─────────────────────────────────────────
# Get all cells of a given type
# Used to find valid swap candidates
# ─────────────────────────────────────────
def build_type_to_cells(cells, cell_positions):
    type_to_cells = {"T0": [], "T1": [], "T2": [], "T3": []}
    for cell_id, cell_type in cells.items():
        if cell_id in cell_positions:
            type_to_cells[cell_type].append(cell_id)
    return type_to_cells

# ─────────────────────────────────────────
# Get all empty sites of a given type
# ─────────────────────────────────────────
def get_empty_sites_of_type(grid, rows, cols, target_type):
    empty = []
    for y in range(1, rows - 1):
        for x in range(1, cols - 1):
            site = grid[y][x]
            if site["site_type"] == target_type and site["occupant"] is None:
                empty.append((x, y))
    return empty

# ─────────────────────────────────────────
# THE MAIN SA LOOP
# ─────────────────────────────────────────
def run_sa(grid, cells, cell_positions, pins, nets, rows, cols, cooling_rate=0.95):

    num_cells = len(cells)
    num_nets = len(nets)

    # Build helper lookup: cell -> which nets it belongs to
    num_components = max(max(pins.keys()), max(cells.keys())) + 1
    cell_to_nets = build_cell_to_nets(nets, num_components)

    # Compute initial cost
    initial_cost = compute_total_hpwl(nets, cell_positions, pins)
    print(f"Initial HPWL: {initial_cost}")

    # Set temperatures
    T = 500 * initial_cost
    T_final = (0.00005 * initial_cost) / num_nets
    moves_per_temp = 20 * num_cells

    print(f"Starting temperature: {T:.2f}")
    print(f"Final temperature:    {T_final:.2f}")
    print(f"Moves per temperature: {moves_per_temp}")
    print(f"Cooling rate: {cooling_rate}")
    print("─" * 40)

    # For graphing later: record (temperature, HPWL) at each step
    history = []

    current_cost = initial_cost
    iteration = 0

    # Build type -> list of cells lookup
    type_to_cells = build_type_to_cells(cells, cell_positions)

    while T > T_final:
        for _ in range(moves_per_temp):

            # Pick a random cell to move
            cell_type = random.choice(["T0", "T1", "T2", "T3"])
            candidates = type_to_cells[cell_type]
            if len(candidates) < 1:
                continue

            cell_a = random.choice(candidates)
            pos_a = cell_positions[cell_a]

            # Decide: swap with another cell or an empty site (50/50)
            swap_with_empty = random.random() < 0.5

            if swap_with_empty:
                # Find empty sites of same type
                empty_sites = get_empty_sites_of_type(grid, rows, cols, cell_type)
                if len(empty_sites) == 0:
                    continue
                pos_b = random.choice(empty_sites)

                # Compute delta cost for moving cell_a to pos_b
                affected_nets = set(cell_to_nets.get(cell_a, []))
                cost_before = sum(compute_hpwl_one_net(nets[i], cell_positions, pins) for i in affected_nets)

                # Temporarily move
                cell_positions[cell_a] = pos_b
                cost_after = sum(compute_hpwl_one_net(nets[i], cell_positions, pins) for i in affected_nets)
                delta = cost_after - cost_before

                # Accept or reject
                if delta < 0 or random.random() < math.exp(-delta / T):
                    # Accept: update grid
                    grid[pos_a[1]][pos_a[0]]["occupant"] = None
                    grid[pos_b[1]][pos_b[0]]["occupant"] = ("CELL", cell_a)
                    current_cost += delta
                else:
                    # Reject: undo
                    cell_positions[cell_a] = pos_a

            else:
                # Swap with another cell of same type
                if len(candidates) < 2:
                    continue
                cell_b = random.choice(candidates)
                if cell_b == cell_a:
                    continue

                pos_b = cell_positions[cell_b]

                # Compute delta
                delta = compute_delta_cost(cell_a, cell_b, cell_positions, pins, nets, cell_to_nets)

                # Accept or reject
                if delta < 0 or random.random() < math.exp(-delta / T):
                    # Accept: do the swap
                    cell_positions[cell_a] = pos_b
                    cell_positions[cell_b] = pos_a
                    grid[pos_a[1]][pos_a[0]]["occupant"] = ("CELL", cell_b)
                    grid[pos_b[1]][pos_b[0]]["occupant"] = ("CELL", cell_a)
                    current_cost += delta

        # Record history for graphing
        history.append((T, current_cost))
        iteration += 1

        if iteration % 10 == 0:
            print(f"Temp: {T:.2f} | HPWL: {current_cost}")

        # Cool down
        T = T * cooling_rate

    print("─" * 40)
    print(f"Final HPWL: {current_cost}")
    return cell_positions, current_cost, history


# ─────────────────────────────────────────
# MAIN — test it on design_1_small
# ─────────────────────────────────────────
def main():
    from parser_step1 import read_file, read_header, read_pins, read_cells, read_nets
    from grid import build_grid, place_pins, initial_placement

    lines = read_file("design_1_small.txt")
    num_components, num_nets, rows, cols, num_pins = read_header(lines[0])
    pins, next_line = read_pins(lines, 1, num_pins)
    num_cells = num_components - num_pins
    cells, next_line = read_cells(lines, next_line, num_cells)
    nets = read_nets(lines, next_line, num_nets)

    grid = build_grid(rows, cols)
    place_pins(grid, pins)
    grid, cell_positions = initial_placement(grid, cells, rows, cols)

    # Run SA with default cooling rate 0.95
    final_positions, final_cost, history = run_sa(
        grid, cells, cell_positions, pins, nets, rows, cols, cooling_rate=0.95
    )

    print(f"\nDone! Final HPWL: {final_cost}")

if __name__ == "__main__":
    main()
