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

def make_initial_placement(cells, legal_sites):
    placement = {}

    random.shuffle(legal_sites["T0"])
    random.shuffle(legal_sites["T1"])
    random.shuffle(legal_sites["T2"])
    random.shuffle(legal_sites["T3"])

    used_count = {
        "T0": 0,
        "T1": 0,
        "T2": 0,
        "T3": 0
    }
    for cell_id in cells:
        cell_type = cells[cell_id]

        site_number = used_count[cell_type]
        position = legal_sites[cell_type][site_number]

        placement[cell_id] = position

        used_count[cell_type] = used_count[cell_type] + 1

    return placement

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

def calculate_total_hpwl(nets, pins, placement):
    total = 0
    for net in nets:
        total += calculate_net_hpwl(net, pins, placement)
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

    for i in range(num_nets):
        line = lines[start + i]
        parts = line.split()

        net = []

        for j in range(1, len(parts)):
            net.append(int(parts[j]))

        nets.append(net)

    return nets

def check_placement_is_legal(rows, cols, pins, cells, placement):
    for pin_id in pins:
        x = pins[pin_id][0]
        y = pins[pin_id][1]

        if x != 0 and x != cols - 1 and y != 0 and y != rows - 1:
            return False

    for cell_id in cells:
        x = placement[cell_id][0]
        y = placement[cell_id][1]

        if x == 0 or x == cols - 1 or y == 0 or y == rows - 1:
            return False

        correct_type = cells[cell_id]
        actual_site_type = get_site_type(x, y)

        if correct_type != actual_site_type:
            return False

    return True

def make_random_same_type_swap(placement, cells):
    cell_ids = list(cells.keys())

    first_cell = random.choice(cell_ids)
    first_type = cells[first_cell]

    same_type_cells = []

    for cell_id in cell_ids:
        if cells[cell_id] == first_type and cell_id != first_cell:
            same_type_cells.append(cell_id)

    second_cell = random.choice(same_type_cells)

    new_placement = placement.copy()

    first_position = new_placement[first_cell]
    second_position = new_placement[second_cell]

    new_placement[first_cell] = second_position
    new_placement[second_cell] = first_position

    return new_placement

def run_sa_demo(placement, cells, nets, pins, rows, cols):
    current_placement = placement
    initial_cost = calculate_total_hpwl(nets, pins, current_placement)

    current_cost = initial_cost

    best_placement = current_placement
    best_cost = initial_cost

    temperature = 500*initial_cost
    while temperature > (5 * 10**-5 * initial_cost) / len(nets):
        for iteration in range(1, 20 * len(cells)):
            new_placement = make_random_same_type_swap(current_placement, cells)
            new_cost = calculate_total_hpwl(nets, pins, new_placement)

            cost_change = new_cost - current_cost

            if cost_change < 0:
                current_placement = new_placement
                current_cost = new_cost
            else:
                accept_probability = math.exp(-cost_change / temperature)
                random_number = random.random()

                if random_number < accept_probability:
                    current_placement = new_placement
                    current_cost = new_cost

            if current_cost < best_cost:
                best_placement = current_placement
                best_cost = current_cost


            is_legal = check_placement_is_legal(rows, cols, pins, cells, best_placement)
            print("Temperature", temperature)
            print("Iteration:", iteration)
            print("Current HPWL:", current_cost)
            print("Best HPWL:", best_cost)
            print("Placement legal:", is_legal)
            print()

        temperature = temperature * 0.95

    return best_placement, best_cost

def main():

    lines = read_file("design_1_small.txt")

    num_components, num_nets, rows, cols, num_pins = read_header(lines[0])

    pins, next_line = read_pins(lines, 1, num_pins)

    num_cells = num_components - num_pins
    cells, next_line = read_cells(lines, next_line, num_cells)

    nets = read_nets(lines, next_line, num_nets)

    legal_sites = make_legal_sites(rows, cols)

    placement = make_initial_placement(cells, legal_sites)

    is_legal = check_placement_is_legal(rows, cols, pins, cells, placement)

    total_hpwl = calculate_total_hpwl(nets, pins, placement)

    new_placement = make_random_same_type_swap(placement, cells)

    new_total_hpwl = calculate_total_hpwl(nets, pins, new_placement)

    new_is_legal = check_placement_is_legal(rows, cols, pins, cells, new_placement)

    best_placement, best_cost = run_sa_demo(placement, cells, nets, pins, rows, cols)


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
    print("Initial placement legal:", is_legal)
    print("After one swap HPWL:", new_total_hpwl)
    print("After one swap legal:", new_is_legal)
    print("Final demo best HPWL:", best_cost)
    print("Final demo placement legal:", check_placement_is_legal(rows, cols, pins, cells, best_placement))

main()
