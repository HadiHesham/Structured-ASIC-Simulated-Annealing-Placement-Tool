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
            legal_sites[cell_type].append([x, y])

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

            if is_cell_position_legal(rows, cols, cell_type, random_site):
                placement[cell_id] = random_site
                available_sites[cell_type].remove(random_site)
                placed = True

    return placement


def build_site_to_cell(placement):
    site_to_cell = {}

    for cell_id in placement:
        position = placement[cell_id]
        site_to_cell[tuple(position)] = cell_id

    return site_to_cell


def get_component_position(component_id, pins, placement):
    if component_id in pins:
        return pins[component_id]

    return placement[component_id]


def calculate_net_hpwl(net, pins, placement):
    x_values = []
    y_values = []

    for component_id in net:
        position = get_component_position(component_id, pins, placement)

        x = position[0]
        y = position[1]

        x_values.append(x)
        y_values.append(y)

    biggest_x = max(x_values)
    smallest_x = min(x_values)

    biggest_y = max(y_values)
    smallest_y = min(y_values)

    width = biggest_x - smallest_x
    height = biggest_y - smallest_y

    hpwl = width + height

    return hpwl


def calculate_affected_hpwl(nets, pins, placement, affected_net_ids):
    total = 0

    for net_id in affected_net_ids:
        net = nets[net_id]
        total = total + calculate_net_hpwl(net, pins, placement)

    return total


def calculate_total_hpwl(nets, pins, placement):
    total = 0

    for net in nets:
        total = total + calculate_net_hpwl(net, pins, placement)

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

        pins[pin_id] = [x, y]

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


def make_random_move_or_swap(placement, cells, legal_sites, site_to_cell):
    new_placement = placement.copy()
    new_site_to_cell = site_to_cell.copy()

    first_cell = random.choice(list(cells.keys()))
    first_type = cells[first_cell]

    random_site = random.choice(legal_sites[first_type])
    random_site_key = tuple(random_site)

    old_position = new_placement[first_cell]
    old_position_key = tuple(old_position)

    cell_on_site = new_site_to_cell.get(random_site_key)

    if random_site == old_position:
        return new_placement, new_site_to_cell, [first_cell]

    if cell_on_site != None:
        new_placement[first_cell] = random_site
        new_placement[cell_on_site] = old_position

        new_site_to_cell[random_site_key] = first_cell
        new_site_to_cell[old_position_key] = cell_on_site

        changed_cells = [first_cell, cell_on_site]
    else:
        new_placement[first_cell] = random_site

        del new_site_to_cell[old_position_key]
        new_site_to_cell[random_site_key] = first_cell

        changed_cells = [first_cell]

    return new_placement, new_site_to_cell, changed_cells


def run_sa_demo(placement, cells, nets, pins, rows, cols, legal_sites, component_to_nets, total_hpwl, site_to_cell):
    current_placement = placement
    current_site_to_cell = site_to_cell

    initial_cost = total_hpwl
    current_cost = initial_cost

    best_placement = current_placement
    best_cost = initial_cost

    temperature = 500 * initial_cost
    final_temperature = (5 * 10**-5 * initial_cost) / len(nets)

    while temperature > final_temperature:
        for iteration in range(1, 20 * len(cells)):

            new_placement, new_site_to_cell, changed_cells = make_random_move_or_swap(
                current_placement, cells, legal_sites, current_site_to_cell
            )

            affected_net_ids = set()

            for cell_id in changed_cells:
                if cell_id in component_to_nets:
                    for net_id in component_to_nets[cell_id]:
                        affected_net_ids.add(net_id)

            old_affected_cost = calculate_affected_hpwl(nets, pins, current_placement, affected_net_ids)
            new_affected_cost = calculate_affected_hpwl(nets, pins, new_placement, affected_net_ids)

            new_cost = current_cost - old_affected_cost + new_affected_cost

            cost_change = new_cost - current_cost

            if cost_change < 0:
                current_placement = new_placement
                current_site_to_cell = new_site_to_cell
                current_cost = new_cost
            else:
                accept_probability = math.exp(-cost_change / temperature)
                random_number = random.random()

                if random_number < accept_probability:
                    current_placement = new_placement
                    current_site_to_cell = new_site_to_cell
                    current_cost = new_cost

            if current_cost < best_cost:
                best_placement = current_placement
                best_cost = current_cost

        temperature = temperature * 0.95

    return best_placement, best_cost


def main():
    lines = read_file("design_1_small.txt")

    num_components, num_nets, rows, cols, num_pins = read_header(lines[0])

    pins, next_line = read_pins(lines, 1, num_pins)

    num_cells = num_components - num_pins
    cells, next_line = read_cells(lines, next_line, num_cells)

    nets, component_to_nets = read_nets(lines, next_line, num_nets)

    legal_sites = make_legal_sites(rows, cols)

    placement = make_initial_placement(cells, legal_sites, rows, cols)

    site_to_cell = build_site_to_cell(placement)

    total_hpwl = calculate_total_hpwl(nets, pins, placement)

    best_placement, best_cost = run_sa_demo(
        placement,
        cells,
        nets,
        pins,
        rows,
        cols,
        legal_sites,
        component_to_nets,
        total_hpwl,
        site_to_cell
    )

    print("File read successfully")
    print("Number of components:", num_components)
    print("Number of nets:", num_nets)
    print("Grid rows:", rows)
    print("Grid cols:", cols)
    print("Number of pins:", num_pins)
    print("Number of movable cells:", num_cells)
    print("First pin:", pins[0])
    print("First cell after pins:", cells[num_pins])
    print("First net:", nets[0])
    print("Total hpwl:", total_hpwl)
    print("Final demo best HPWL:", best_cost)


main()
