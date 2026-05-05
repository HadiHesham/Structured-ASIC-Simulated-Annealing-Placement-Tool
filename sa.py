import math
import random

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

    if min_x == float('inf'):
        return 0
    return (max_x - min_x) + (max_y - min_y)

def compute_total_hpwl(nets, cell_positions, pins):
    total = 0
    for net in nets:
        total += compute_hpwl_one_net(net, cell_positions, pins)
    return total

def run_sa(grid, cells, cell_positions, pins, nets, rows, cols, cooling_rate=0.95):

    num_cells = len(cells)
    num_nets = len(nets)

    # Compute initial cost
    initial_cost = compute_total_hpwl(nets, cell_positions, pins)
    print(f"Initial HPWL: {initial_cost}")

    # Set temperatures
    T = 500 * initial_cost
    T_final = (0.00005 * initial_cost) / num_nets
    moves_per_temp = 20 * num_cells

    print(f"Starting temperature: {T:.2f}")
    print(f"Final temperature:    {T_final:.4f}")
    print(f"Moves per temperature: {moves_per_temp}")
    print(f"Cooling rate: {cooling_rate}")
    print("-" * 40)

    # Group cells by type for easy lookup
    type_to_cells = {"T0": [], "T1": [], "T2": [], "T3": []}
    for cell_id, cell_type in cells.items():
        type_to_cells[cell_type].append(cell_id)

    current_cost = initial_cost
    history = []

    while T > T_final:

        for _ in range(moves_per_temp):

            # Pick a random cell type that has at least 2 cells
            cell_type = random.choice(["T0", "T1", "T2", "T3"])
            candidates = type_to_cells[cell_type]
            if len(candidates) < 2:
                continue

            # Pick two different cells of the same type
            cell_a = random.choice(candidates)
            cell_b = random.choice(candidates)
            if cell_a == cell_b:
                continue

            # Get their positions
            pos_a = cell_positions[cell_a]
            pos_b = cell_positions[cell_b]

            # Compute cost before swap
            cost_before = current_cost

            # Do the swap temporarily
            cell_positions[cell_a] = pos_b
            cell_positions[cell_b] = pos_a

            # Compute cost after swap
            cost_after = compute_total_hpwl(nets, cell_positions, pins)
            delta = cost_after - cost_before

            # Accept or reject
            if delta < 0 or random.random() < math.exp(-delta / T):
                # Accept: update grid occupants
                grid[pos_a[1]][pos_a[0]]["occupant"] = ("CELL", cell_b)
                grid[pos_b[1]][pos_b[0]]["occupant"] = ("CELL", cell_a)
                current_cost = cost_after
            else:
                # Reject: undo the swap
                cell_positions[cell_a] = pos_a
                cell_positions[cell_b] = pos_b

        # Record for graphing later
        history.append((T, current_cost))

        # Cool down
        T = T * cooling_rate

    print("-" * 40)
    print(f"Final HPWL: {current_cost}")
    return cell_positions, current_cost, history


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

    final_positions, final_cost, history = run_sa(
        grid, cells, cell_positions, pins, nets, rows, cols, cooling_rate=0.95
    )

if __name__ == "__main__":
    main()
