def print_grid(grid, rows, cols):
    # Print the full grid to the console
    # P = Pin, 0/1/2/3 = Cell type, . = Empty site

    for y in range(rows):
        row_str = ""
        for x in range(cols):
            site = grid[y][x]
            occupant = site["occupant"]

            if occupant is None:
                row_str += ". "
            elif occupant[0] == "PIN":
                row_str += "P "
            elif occupant[0] == "CELL":
                # Get the cell type number (T0->0, T1->1, etc.)
                cell_type = site["site_type"]
                row_str += cell_type[1] + " "  # T0 -> "0", T1 -> "1"

        print(row_str)


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

    print("Grid after initial placement:")
    print()
    print_grid(grid, rows, cols)


if __name__ == "__main__":
    main()
