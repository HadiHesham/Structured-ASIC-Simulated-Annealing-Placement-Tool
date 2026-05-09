import random
import math

MASTER_TILE = [
    ["T0", "T1", "T0", "T2", "T0"],
    ["T1", "T0", "T1", "T0", "T1"],
    ["T0", "T2", "T3", "T0", "T2"],
    ["T1", "T0", "T1", "T0", "T0"],
    ["T0", "T0", "T0", "T0", "T0"],
]


def get_site_type(x, y):
    small_x = (x - 1) % 5
    small_y = (y - 1) % 5
    return MASTER_TILE[small_y][small_x]


def make_legal_sites(rows, cols):
    legal_sites = {
        "T0": [],
        "T1": [],
        "T2": [],
        "T3": []
    }

    for y in range(1, rows - 1):
        for x in range(1, cols - 1):
            cell_type = get_site_type(x, y)
            legal_sites[cell_type].append((x, y))

    return legal_sites


def is_cell_position_legal(rows, cols, cell_type, position):
    x = position[0]
    y = position[1]

    if x == 0 or x == cols - 1 or y == 0 or y == rows - 1:
        return False

    actual_site_type = get_site_type(x, y)

    if cell_type != actual_site_type:
        return False

    return True


def make_initial_placement(cells, legal_sites, rows, cols):
    placement = {}

    available_sites = {
        "T0": legal_sites["T0"].copy(),
        "T1": legal_sites["T1"].copy(),
        "T2": legal_sites["T2"].copy(),
        "T3": legal_sites["T3"].copy()
    }

    for cell_id in cells:
        cell_type = cells[cell_id]

        placed = False

        while placed == False:
            random_site = random.choice(available_sites[cell_type])
            placement[cell_id] = tuple(random_site)
            available_sites[cell_type].remove(random_site)
            placed = True

    return placement


def build_site_to_cell(placement):
    site_to_cell = {}

    for cell_id in placement:
        position = placement[cell_id]
        site_to_cell[position] = cell_id

    return site_to_cell


def calculate_net_hpwl(net, net_length, placement):
    x, y = placement[net[0]]
    smallest_x = biggest_x = x
    smallest_y = biggest_y = y

    for i in range(1, net_length):
        x, y = placement[net[i]]

        if x < smallest_x:
            smallest_x = x
        if x > biggest_x:
            biggest_x = x
        if y < smallest_y:
            smallest_y = y
        if y > biggest_y:
            biggest_y = y

    return (biggest_x - smallest_x) + (biggest_y - smallest_y)


def calculate_affected_hpwl(nets, net_lengths, placement, affected_net_ids):
    total = 0

    for net_id in affected_net_ids:
        total = total + calculate_net_hpwl(nets[net_id], net_lengths[net_id], placement)

    return total


def calculate_total_hpwl(nets, net_lengths, placement):
    total = 0

    for i, net in enumerate(nets):
        total = total + calculate_net_hpwl(net, net_lengths[i], placement)

    return total


def read_file(filename):
    file = open(filename, "r")
    lines = file.readlines()
    file.close()

    clean_lines = []

    for line in lines:
        line = line.strip()
        if line != "":
            clean_lines.append(line)

    return clean_lines


def read_header(first_line):
    parts = first_line.split()

    num_components = int(parts[0])
    num_nets = int(parts[1])
    rows = int(parts[2])
    cols = int(parts[3])
    num_pins = int(parts[4])

    return num_components, num_nets, rows, cols, num_pins


def read_pins(lines, start, num_pins):
    pins = {}

    for i in range(num_pins):
        line = lines[start + i]
        parts = line.split()

        pin_id = int(parts[0])
        x = int(parts[1])
        y = int(parts[2])

        pins[pin_id] = (x, y)

    next_line = start + num_pins
    return pins, next_line


def read_cells(lines, start, num_cells):
    cells = {}

    for i in range(num_cells):
        line = lines[start + i]
        parts = line.split()

        cell_id = int(parts[0])
        cell_type = parts[1]

        cells[cell_id] = cell_type

    next_line = start + num_cells
    return cells, next_line


def read_nets(lines, start, num_nets):
    nets = []
    component_to_nets = {}

    for net_index in range(num_nets):
        line = lines[start + net_index]
        parts = line.split()

        net = []

        for j in range(1, len(parts)):
            component_id = int(parts[j])
            net.append(component_id)

            if component_id not in component_to_nets:
                component_to_nets[component_id] = []

            component_to_nets[component_id].append(net_index)

        nets.append(net)

    return nets, component_to_nets


def apply_move(placement, site_to_cell, first_cell, old_pos, new_pos, cell_on_site):
    placement[first_cell] = new_pos
    site_to_cell[new_pos] = first_cell

    if cell_on_site is not None:
        placement[cell_on_site] = old_pos
        site_to_cell[old_pos] = cell_on_site
    else:
        del site_to_cell[old_pos]


def undo_move(placement, site_to_cell, first_cell, old_pos, new_pos, cell_on_site):
    apply_move(placement, site_to_cell, first_cell, new_pos, old_pos, cell_on_site)


def calculate_cell_costs(cell_ids, component_to_nets, nets, net_lengths, placement):
    cell_costs = {}

    for cell_id in cell_ids:
        total = 0
        if cell_id in component_to_nets:
            for net_id in component_to_nets[cell_id]:
                total = total + calculate_net_hpwl(nets[net_id], net_lengths[net_id], placement)
        cell_costs[cell_id] = total

    return cell_costs


def pick_move(placement, cells, legal_sites, site_to_cell, cell_ids, cell_costs, total_cost):
    random_value = random.uniform(0, total_cost)

    first_cell = cell_ids[-1]
    cumulative = 0
    for cell_id in cell_ids:
        cumulative += cell_costs[cell_id]
        if cumulative >= random_value:
            first_cell = cell_id
            break

    first_type = cells[first_cell]
    sites = legal_sites[first_type]
    new_pos = sites[random.randint(0, len(sites) - 1)]
    old_pos = placement[first_cell]
    cell_on_site = site_to_cell.get(new_pos)

    return first_cell, old_pos, new_pos, cell_on_site


def run_sa_demo(placement, cells, nets, net_lengths, pins, rows, cols, legal_sites, component_to_nets, total_hpwl, site_to_cell, cell_ids):
    current_placement = placement
    current_site_to_cell = site_to_cell

    initial_cost = total_hpwl
    current_cost = initial_cost

    best_placement = current_placement
    best_cost = initial_cost

    temperature = 500 * initial_cost
    initial_temperature = temperature
    final_temperature = (5 * 10**-5 * initial_cost) / len(nets)

    cell_costs = calculate_cell_costs(cell_ids, component_to_nets, nets, net_lengths, current_placement)
    total_cost = sum(cell_costs[cell_id] for cell_id in cell_ids)

    while temperature > final_temperature:
        for iteration in range(1, 20 * len(cells)):

            first_cell, old_pos, new_pos, cell_on_site = pick_move(
                current_placement, cells, legal_sites, current_site_to_cell, cell_ids, cell_costs, total_cost
            )

            if cell_on_site is not None:
                affected_net_ids = set(component_to_nets.get(first_cell, [])) | set(component_to_nets.get(cell_on_site, []))
            else:
                affected_net_ids = set(component_to_nets.get(first_cell, []))

            old_affected_cost = calculate_affected_hpwl(nets, net_lengths, current_placement, affected_net_ids)

            apply_move(current_placement, current_site_to_cell, first_cell, old_pos, new_pos, cell_on_site)

            new_affected_cost = calculate_affected_hpwl(nets, net_lengths, current_placement, affected_net_ids)

            new_cost = current_cost - old_affected_cost + new_affected_cost
            cost_change = new_cost - current_cost

            if cost_change < 0 or random.random() < math.exp(-cost_change / temperature):
                current_cost = new_cost
                delta = new_affected_cost - old_affected_cost
                cell_costs[first_cell] += delta
                total_cost += delta
                if cell_on_site is not None:
                    cell_costs[cell_on_site] += delta
                    total_cost += delta
            else:
                undo_move(current_placement, current_site_to_cell, first_cell, old_pos, new_pos, cell_on_site)

            if current_cost < best_cost:
                best_placement = current_placement.copy()
                best_cost = current_cost

        cooling_rate = 0.95 + 0.04 * (temperature / initial_temperature)
        temperature = temperature * cooling_rate

    return best_placement, best_cost


def main():
    lines = read_file("design_5_extreme.txt")

    num_components, num_nets, rows, cols, num_pins = read_header(lines[0])

    pins, next_line = read_pins(lines, 1, num_pins)

    num_cells = num_components - num_pins

    cells, next_line = read_cells(lines, next_line, num_cells)

    cell_ids = list(cells.keys())

    nets, component_to_nets = read_nets(lines, next_line, num_nets)

    legal_sites = make_legal_sites(rows, cols)

    placement = make_initial_placement(cells, legal_sites, rows, cols)

    site_to_cell = build_site_to_cell(placement)

    for pin_id in pins:
        placement[pin_id] = pins[pin_id]

    net_lengths = [len(net) for net in nets]

    total_hpwl = calculate_total_hpwl(nets, net_lengths, placement)

    best_placement, best_cost = run_sa_demo(
        placement,
        cells,
        nets,
        net_lengths,
        pins,
        rows,
        cols,
        legal_sites,
        component_to_nets,
        total_hpwl,
        site_to_cell,
        cell_ids
    )

    print("Total hpwl:", total_hpwl)
    print("Final demo best HPWL:", best_cost)


main()
