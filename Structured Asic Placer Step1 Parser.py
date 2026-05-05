MASTER_TILE = [
    ["T0", "T1", "T0", "T2", "T0"],
    ["T1", "T0", "T1", "T0", "T1"],
    ["T0", "T2", "T3", "T0", "T2"],
    ["T1", "T0", "T1", "T0", "T0"],
    ["T0", "T0", "T0", "T0", "T0"],
]


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


main()