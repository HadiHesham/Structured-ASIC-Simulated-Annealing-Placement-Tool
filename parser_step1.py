#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <random>
#include <cmath>
#include <algorithm>
#include <cstdlib>
#include <climits>

using namespace std;

mt19937 rng(random_device{}());

const int CANDIDATES_PER_MOVE = 5;

int num_components;
int num_nets;
int rows;
int cols;
int num_pins;
int num_cells;

int MASTER_TILE[5][5] = {
    {0, 1, 0, 2, 0},
    {1, 0, 1, 0, 1},
    {0, 2, 3, 0, 2},
    {1, 0, 1, 0, 0},
    {0, 0, 0, 0, 0}
};

vector<pair<int,int>> placement;
vector<pair<int,int>> original_pin_placement;
vector<int> cell_type;
vector<int> cell_ids;
vector<int> pin_ids;
vector<vector<int>> nets;
vector<vector<int>> component_to_nets;
vector<pair<int,int>> legal_sites[4];

vector<int> site_to_cell;
vector<bool> fixed_site;

vector<int> affected_mark;
int affected_stamp = 1;

vector<int> net_hpwl;

int get_random_index(int size) {
    return rng() % size;
}

int get_site_index(int x, int y) {
    return y * cols + x;
}

int get_site_index(pair<int,int> pos) {
    return pos.second * cols + pos.first;
}

int get_site_type(int x, int y) {
    int small_x = (x - 1) % 5;
    int small_y = (y - 1) % 5;

    return MASTER_TILE[small_y][small_x];
}

void read_input_file(string filename) {
    ifstream file(filename);

    if (!file.is_open()) {
        cout << "ERROR: Could not open input file: " << filename << endl;
        exit(1);
    }

    file >> num_components;
    file >> num_nets;
    file >> rows;
    file >> cols;
    file >> num_pins;

    placement.resize(num_components);
    original_pin_placement.resize(num_components);
    cell_type.resize(num_components);
    nets.resize(num_nets);
    component_to_nets.resize(num_components);
    site_to_cell.resize(rows * cols, -1);
    fixed_site.resize(rows * cols, false);

    for (int i = 0; i < num_pins; i++) {
        int pin_id;
        int x;
        int y;
        string p;

        file >> pin_id >> x >> y >> p;

        placement[pin_id] = {x, y};
        original_pin_placement[pin_id] = {x, y};
        pin_ids.push_back(pin_id);

        if (x >= 0 && x < cols && y >= 0 && y < rows) {
            fixed_site[get_site_index(x, y)] = true;
        }
    }

    num_cells = num_components - num_pins;

    for (int i = 0; i < num_cells; i++) {
        int cell_id;
        string type_string;

        file >> cell_id >> type_string;

        int type = type_string[1] - '0';

        cell_type[cell_id] = type;
        cell_ids.push_back(cell_id);
    }

    for (int net_id = 0; net_id < num_nets; net_id++) {
        int count;

        file >> count;

        for (int j = 0; j < count; j++) {
            int component_id;

            file >> component_id;

            nets[net_id].push_back(component_id);
            component_to_nets[component_id].push_back(net_id);
        }
    }

    file.close();
}

void make_legal_sites() {
    for (int type = 0; type < 4; type++) {
        legal_sites[type].clear();
    }

    for (int y = 1; y < rows - 1; y++) {
        for (int x = 1; x < cols - 1; x++) {
            int type = get_site_type(x, y);
            legal_sites[type].push_back({x, y});
        }
    }
}

void make_initial_placement() {
    fill(site_to_cell.begin(), site_to_cell.end(), -1);

    vector<pair<int,int>> available_sites[4];

    for (int type = 0; type < 4; type++) {
        available_sites[type] = legal_sites[type];
        shuffle(available_sites[type].begin(), available_sites[type].end(), rng);
    }

    int used_count[4] = {0, 0, 0, 0};

    for (int cell_id : cell_ids) {
        int type = cell_type[cell_id];

        placement[cell_id] = available_sites[type][used_count[type]];

        site_to_cell[get_site_index(placement[cell_id])] = cell_id;

        used_count[type]++;
    }
}

void build_site_to_cell() {
    fill(site_to_cell.begin(), site_to_cell.end(), -1);

    for (int cell_id : cell_ids) {
        pair<int,int> pos = placement[cell_id];
        site_to_cell[get_site_index(pos)] = cell_id;
    }
}

int calculate_net_hpwl(int net_id) {
    int first = nets[net_id][0];

    int min_x = placement[first].first;
    int max_x = min_x;
    int min_y = placement[first].second;
    int max_y = min_y;

    for (int i = 1; i < (int)nets[net_id].size(); i++) {
        int component_id = nets[net_id][i];

        int x = placement[component_id].first;
        int y = placement[component_id].second;

        if (x < min_x) {
            min_x = x;
        }

        if (x > max_x) {
            max_x = x;
        }

        if (y < min_y) {
            min_y = y;
        }

        if (y > max_y) {
            max_y = y;
        }
    }

    return (max_x - min_x) + (max_y - min_y);
}

int initialize_net_hpwl() {
    int total = 0;

    net_hpwl.resize(num_nets);

    for (int net_id = 0; net_id < num_nets; net_id++) {
        net_hpwl[net_id] = calculate_net_hpwl(net_id);
        total += net_hpwl[net_id];
    }

    return total;
}

void get_affected_net_ids_fast(
    int first_cell,
    int second_cell,
    vector<int>& affected_net_ids
) {
    affected_net_ids.clear();

    if (affected_stamp == INT_MAX) {
        fill(affected_mark.begin(), affected_mark.end(), 0);
        affected_stamp = 1;
    } else {
        affected_stamp++;
    }

    for (int net_id : component_to_nets[first_cell]) {
        if (affected_mark[net_id] != affected_stamp) {
            affected_mark[net_id] = affected_stamp;
            affected_net_ids.push_back(net_id);
        }
    }

    if (second_cell != -1) {
        for (int net_id : component_to_nets[second_cell]) {
            if (affected_mark[net_id] != affected_stamp) {
                affected_mark[net_id] = affected_stamp;
                affected_net_ids.push_back(net_id);
            }
        }
    }
}

void apply_move(
    int first_cell,
    pair<int,int> old_pos,
    pair<int,int> new_pos,
    int cell_on_site
) {
    int old_index = get_site_index(old_pos);
    int new_index = get_site_index(new_pos);

    placement[first_cell] = new_pos;
    site_to_cell[new_index] = first_cell;

    if (cell_on_site != -1) {
        placement[cell_on_site] = old_pos;
        site_to_cell[old_index] = cell_on_site;
    } else {
        site_to_cell[old_index] = -1;
    }
}

void undo_move(
    int first_cell,
    pair<int,int> old_pos,
    pair<int,int> new_pos,
    int cell_on_site
) {
    apply_move(
        first_cell,
        new_pos,
        old_pos,
        cell_on_site
    );
}

int get_radius_from_temperature(double temperature, double initial_temperature) {
    double ratio = temperature / initial_temperature;

    if (ratio > 0.05) {
        return -1;
    }

    if (ratio > 0.005) {
        return 20;
    }

    if (ratio > 0.0005) {
        return 10;
    }

    return 5;
}

bool pick_global_site(
    int type,
    pair<int,int> old_pos,
    pair<int,int>& new_pos,
    int& cell_on_site
) {
    for (int attempt = 0; attempt < 100; attempt++) {
        new_pos = legal_sites[type][get_random_index(legal_sites[type].size())];

        if (new_pos == old_pos) {
            continue;
        }

        int index = get_site_index(new_pos);

        if (fixed_site[index]) {
            continue;
        }

        cell_on_site = site_to_cell[index];

        return true;
    }

    return false;
}

bool pick_local_site(
    int type,
    pair<int,int> old_pos,
    int radius,
    pair<int,int>& new_pos,
    int& cell_on_site
) {
    int range = 2 * radius + 1;

    for (int attempt = 0; attempt < 80; attempt++) {
        int dx = (int)(rng() % range) - radius;
        int dy = (int)(rng() % range) - radius;

        if (dx == 0 && dy == 0) {
            continue;
        }

        int x = old_pos.first + dx;
        int y = old_pos.second + dy;

        if (x <= 0 || x >= cols - 1 || y <= 0 || y >= rows - 1) {
            continue;
        }

        if (get_site_type(x, y) != type) {
            continue;
        }

        int index = get_site_index(x, y);

        if (fixed_site[index]) {
            continue;
        }

        new_pos = {x, y};
        cell_on_site = site_to_cell[index];

        return true;
    }

    return false;
}

void pick_move(
    int& first_cell,
    pair<int,int>& old_pos,
    pair<int,int>& new_pos,
    int& cell_on_site,
    int move_radius
) {
    first_cell = cell_ids[get_random_index(cell_ids.size())];

    int type = cell_type[first_cell];

    old_pos = placement[first_cell];

    bool success = false;

    if (move_radius == -1) {
        success = pick_global_site(type, old_pos, new_pos, cell_on_site);
    } else {
        success = pick_local_site(type, old_pos, move_radius, new_pos, cell_on_site);

        if (!success) {
            success = pick_global_site(type, old_pos, new_pos, cell_on_site);
        }
    }

    if (!success) {
        new_pos = old_pos;
        cell_on_site = -1;
    }
}

int evaluate_move_delta(
    int first_cell,
    pair<int,int> old_pos,
    pair<int,int> new_pos,
    int cell_on_site,
    vector<int>& affected_net_ids,
    vector<int>& new_net_hpwl_values
) {
    get_affected_net_ids_fast(
        first_cell,
        cell_on_site,
        affected_net_ids
    );

    int old_affected_cost = 0;

    for (int net_id : affected_net_ids) {
        old_affected_cost += net_hpwl[net_id];
    }

    apply_move(
        first_cell,
        old_pos,
        new_pos,
        cell_on_site
    );

    int new_affected_cost = 0;
    new_net_hpwl_values.clear();

    for (int net_id : affected_net_ids) {
        int new_hpwl = calculate_net_hpwl(net_id);
        new_net_hpwl_values.push_back(new_hpwl);
        new_affected_cost += new_hpwl;
    }

    undo_move(
        first_cell,
        old_pos,
        new_pos,
        cell_on_site
    );

    return new_affected_cost - old_affected_cost;
}

int run_sa(int total_hpwl) {
    int current_cost = total_hpwl;
    int best_cost = current_cost;

    vector<pair<int,int>> best_placement = placement;

    double temperature = 500.0 * total_hpwl;
    double initial_temperature = temperature;
    double final_temperature = (5e-5 * total_hpwl) / num_nets;

    vector<int> affected_net_ids;
    affected_net_ids.reserve(128);

    vector<int> new_net_hpwl_values;
    new_net_hpwl_values.reserve(128);

    vector<int> best_affected_net_ids;
    best_affected_net_ids.reserve(128);

    vector<int> best_new_net_hpwl_values;
    best_new_net_hpwl_values.reserve(128);

    while (temperature > final_temperature) {
        int move_radius = get_radius_from_temperature(temperature, initial_temperature);

        for (int iteration = 0; iteration < 20 * num_cells; iteration++) {
            int best_first_cell = -1;
            pair<int,int> best_old_pos;
            pair<int,int> best_new_pos;
            int best_cell_on_site = -1;
            int best_delta = INT_MAX;

            for (int candidate = 0; candidate < CANDIDATES_PER_MOVE; candidate++) {
                int first_cell;
                pair<int,int> old_pos;
                pair<int,int> new_pos;
                int cell_on_site;

                pick_move(
                    first_cell,
                    old_pos,
                    new_pos,
                    cell_on_site,
                    move_radius
                );

                if (new_pos == old_pos) {
                    continue;
                }

                int delta = evaluate_move_delta(
                    first_cell,
                    old_pos,
                    new_pos,
                    cell_on_site,
                    affected_net_ids,
                    new_net_hpwl_values
                );

                if (delta < best_delta) {
                    best_delta = delta;
                    best_first_cell = first_cell;
                    best_old_pos = old_pos;
                    best_new_pos = new_pos;
                    best_cell_on_site = cell_on_site;
                    best_affected_net_ids = affected_net_ids;
                    best_new_net_hpwl_values = new_net_hpwl_values;
                }
            }

            if (best_first_cell == -1) {
                continue;
            }

            double random_value = (double)rng() / (double)rng.max();

            if (best_delta < 0 || random_value < exp(-best_delta / temperature)) {
                apply_move(
                    best_first_cell,
                    best_old_pos,
                    best_new_pos,
                    best_cell_on_site
                );

                current_cost += best_delta;

                for (int i = 0; i < (int)best_affected_net_ids.size(); i++) {
                    net_hpwl[best_affected_net_ids[i]] = best_new_net_hpwl_values[i];
                }

                if (current_cost < best_cost) {
                    best_cost = current_cost;
                    best_placement = placement;
                }
            }
        }

        temperature *= 0.95;
    }

    placement = best_placement;

    build_site_to_cell();

    return best_cost;
}

bool verify_placement() {
    vector<int> seen(rows * cols, -1);

    for (int pin_id : pin_ids) {
        pair<int,int> pos = placement[pin_id];

        if (placement[pin_id] != original_pin_placement[pin_id]) {
            cout << "ERROR: Pin " << pin_id << " moved" << endl;
            return false;
        }

        if (pos.first >= 0 && pos.first < cols && pos.second >= 0 && pos.second < rows) {
            seen[get_site_index(pos)] = pin_id;
        }
    }

    for (int cell_id : cell_ids) {
        pair<int,int> pos = placement[cell_id];

        int index = get_site_index(pos);

        if (seen[index] != -1) {
            cout << "ERROR: Cell " << cell_id
                 << " overlaps with component "
                 << seen[index] << endl;
            return false;
        }

        seen[index] = cell_id;

        if (pos.first <= 0 || pos.first >= cols - 1 || pos.second <= 0 || pos.second >= rows - 1) {
            cout << "ERROR: Cell " << cell_id << " is outside legal area" << endl;
            return false;
        }

        int actual_type = get_site_type(pos.first, pos.second);

        if (actual_type != cell_type[cell_id]) {
            cout << "ERROR: Cell " << cell_id << " is on wrong site type" << endl;
            return false;
        }
    }

    cout << "Placement is VALID" << endl;

    return true;
}

int main() {
    string filename = "design_5_extreme.txt";

    read_input_file(filename);

    affected_mark.resize(num_nets, 0);

    make_legal_sites();

    make_initial_placement();

    build_site_to_cell();

    int total_hpwl = initialize_net_hpwl();

    int best_cost = run_sa(total_hpwl);

    cout << "Initial total HPWL: " << total_hpwl << endl;
    cout << "Final best HPWL: " << best_cost << endl;

    verify_placement();

    return 0;
}
