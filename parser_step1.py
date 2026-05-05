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



def main():

    lines = read_file("design_1_small.txt")

    num_components, num_nets, rows, cols, num_pins = read_header(lines[0])

    pins, next_line = read_pins(lines, 1, num_pins)

    num_cells = num_components - num_pins
    cells, next_line = read_cells(lines, next_line, num_cells)

    nets = read_nets(lines, next_line, num_nets)

    legal_sites = make_legal_sites(rows, cols)

    placement = make_initial_placement(cells, legal_sites)

    total_hpwl = calculate_total_hpwl(nets, pins, placement)

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


main()
