#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <unordered_map>
#include <random>
#include <cmath>
#include <algorithm>

using namespace std;

mt19937 rng(random_device{}());

struct PairHash {
    size_t operator()(const pair<int,int>& p) const {
        return hash<int>()(p.first) ^ (hash<int>()(p.second) << 16);
    }
};

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
vector<int> cell_type;
vector<int> cell_ids;
vector<vector<int>> nets;
vector<vector<int>> component_to_nets;
vector<pair<int,int>> legal_sites[4];
unordered_map<pair<int,int>, int, PairHash> site_to_cell;

int get_random_index(int size) {
    return rng() % size;
}

int get_site_type(int x, int y) {
    int small_x = (x - 1) % 5;
    int small_y = (y - 1) % 5;
    return MASTER_TILE[small_y][small_x];
}

void read_input_file(string filename) {
    ifstream file(filename);

    file >> num_components;
    file >> num_nets;
    file >> rows;
    file >> cols;
    file >> num_pins;

    placement.resize(num_components);
    cell_type.resize(num_components);
    nets.resize(num_nets);
    component_to_nets.resize(num_components);

    for (int i = 0; i < num_pins; i++) {
        int pin_id, x, y;
        string p;
        file >> pin_id >> x >> y >> p;
        placement[pin_id] = {x, y};
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
    for (int y = 1; y < rows - 1; y++)
        for (int x = 1; x < cols - 1; x++)
            legal_sites[get_site_type(x, y)].push_back({x, y});
}

void make_initial_placement() {
    vector<pair<int,int>> available_sites[4];
    for (int type = 0; type < 4; type++) {
        available_sites[type] = legal_sites[type];
        shuffle(available_sites[type].begin(), available_sites[type].end(), rng);
    }

    int used_count[4] = {0, 0, 0, 0};
    for (int cell_id : cell_ids) {
        int type = cell_type[cell_id];
        placement[cell_id] = available_sites[type][used_count[type]];
        used_count[type]++;
    }
}

void build_site_to_cell() {
    site_to_cell.clear();
    for (int cell_id : cell_ids)
        site_to_cell[placement[cell_id]] = cell_id;
}

int calculate_net_hpwl(int net_id) {
    int first = nets[net_id][0];
    int min_x = placement[first].first, max_x = min_x;
    int min_y = placement[first].second, max_y = min_y;

    for (int i = 1; i < (int)nets[net_id].size(); i++) {
        int c = nets[net_id][i];
        int x = placement[c].first;
        int y = placement[c].second;
        if (x < min_x) min_x = x;
        if (x > max_x) max_x = x;
        if (y < min_y) min_y = y;
        if (y > max_y) max_y = y;
    }

    return (max_x - min_x) + (max_y - min_y);
}

int calculate_total_hpwl() {
    int total = 0;
    for (int net_id = 0; net_id < num_nets; net_id++)
        total += calculate_net_hpwl(net_id);
    return total;
}

vector<bool> affected_flag;

vector<int> get_affected_net_ids(vector<int>& changed_cells) {
    vector<int> affected_net_ids;
    for (int cell_id : changed_cells)
        for (int net_id : component_to_nets[cell_id])
            if (!affected_flag[net_id]) {
                affected_flag[net_id] = true;
                affected_net_ids.push_back(net_id);
            }
    for (int id : affected_net_ids)
        affected_flag[id] = false;
    return affected_net_ids;
}

int calculate_affected_hpwl(vector<int>& affected_net_ids) {
    int total = 0;
    for (int net_id : affected_net_ids)
        total += calculate_net_hpwl(net_id);
    return total;
}

void apply_move(int first_cell, pair<int,int> old_pos, pair<int,int> new_pos, int cell_on_site) {
    placement[first_cell] = new_pos;
    site_to_cell[new_pos] = first_cell;
    if (cell_on_site != -1) {
        placement[cell_on_site] = old_pos;
        site_to_cell[old_pos] = cell_on_site;
    } else {
        site_to_cell.erase(old_pos);
    }
}

void undo_move(int first_cell, pair<int,int> old_pos, pair<int,int> new_pos, int cell_on_site) {
    apply_move(first_cell, new_pos, old_pos, cell_on_site);
}

void pick_move(int& first_cell, pair<int,int>& old_pos, pair<int,int>& new_pos, int& cell_on_site) {
    first_cell = cell_ids[get_random_index(cell_ids.size())];
    int type = cell_type[first_cell];
    new_pos = legal_sites[type][get_random_index(legal_sites[type].size())];
    old_pos = placement[first_cell];

    auto it = site_to_cell.find(new_pos);
    cell_on_site = (it != site_to_cell.end()) ? it->second : -1;
}

int run_sa(int total_hpwl) {
    int current_cost = total_hpwl;
    int best_cost = current_cost;

    double temperature = 500.0 * total_hpwl;
    double final_temperature = (5e-5 * total_hpwl) / num_nets;

    uniform_real_distribution<double> probability(0.0, 1.0);

    while (temperature > final_temperature) {
        for (int iteration = 0; iteration < 20 * num_cells; iteration++) {
            int first_cell;
            pair<int,int> old_pos, new_pos;
            int cell_on_site;

            pick_move(first_cell, old_pos, new_pos, cell_on_site);

            if (new_pos == old_pos) continue;

            vector<int> changed_cells = {first_cell};
            if (cell_on_site != -1) changed_cells.push_back(cell_on_site);

            vector<int> affected_net_ids = get_affected_net_ids(changed_cells);

            int old_affected_cost = calculate_affected_hpwl(affected_net_ids);
            apply_move(first_cell, old_pos, new_pos, cell_on_site);
            int new_affected_cost = calculate_affected_hpwl(affected_net_ids);

            int new_cost = current_cost - old_affected_cost + new_affected_cost;
            int cost_change = new_cost - current_cost;

            if (cost_change < 0 || probability(rng) < exp(-cost_change / temperature)) {
                current_cost = new_cost;
            } else {
                undo_move(first_cell, old_pos, new_pos, cell_on_site);
            }

            if (current_cost < best_cost)
                best_cost = current_cost;
        }

        temperature *= 0.95;
    }

    return best_cost;
}

int main() {
    cout << "RUNNING parser_step1.cpp NEW VERSION" << endl;
    string filename = "design_5_extreme.txt";

    read_input_file(filename);
    affected_flag.resize(num_nets, false);

    make_legal_sites();
    make_initial_placement();
    build_site_to_cell();

    int total_hpwl = calculate_total_hpwl();
    int best_cost = run_sa(total_hpwl);

    cout << "File read successfully" << endl;
    cout << "Input file: " << filename << endl;
    cout << "Number of components: " << num_components << endl;
    cout << "Number of nets: " << num_nets << endl;
    cout << "Grid rows: " << rows << endl;
    cout << "Grid cols: " << cols << endl;
    cout << "Number of pins: " << num_pins << endl;
    cout << "Number of movable cells: " << num_cells << endl;
    cout << "Initial total HPWL: " << total_hpwl << endl;
    cout << "Final best HPWL: " << best_cost << endl;

    return 0;
}
