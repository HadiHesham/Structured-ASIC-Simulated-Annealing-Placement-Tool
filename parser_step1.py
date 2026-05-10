#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <unordered_map>
#include <random>
#include <cmath>
#include <algorithm>
#include <cstdlib>

using namespace std;

mt19937 rng(random_device{}());

struct PairHash {
    size_t operator()(const pair<int, int>& p) const {
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

vector<pair<int, int>> placement;
vector<pair<int, int>> original_pin_placement;
vector<int> cell_type;
vector<int> cell_ids;
vector<int> pin_ids;
vector<vector<int>> nets;
vector<vector<int>> component_to_nets;
vector<pair<int, int>> legal_sites[4];

vector<bool> is_pin;
vector<bool> is_cell;
vector<bool> affected_flag;

unordered_map<pair<int, int>, int, PairHash> site_to_cell;
unordered_map<pair<int, int>, int, PairHash> fixed_pin_site;

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
    original_pin_placement.resize(num_components);
    cell_type.resize(num_components);
    nets.resize(num_nets);
    component_to_nets.resize(num_components);
    is_pin.resize(num_components, false);
    is_cell.resize(num_components, false);

    for (int i = 0; i < num_pins; i++) {
        int pin_id;
        int x;
        int y;
        string p;

        file >> pin_id;
        file >> x;
        file >> y;
        file >> p;

        placement[pin_id] = {x, y};
        original_pin_placement[pin_id] = {x, y};
        pin_ids.push_back(pin_id);
        is_pin[pin_id] = true;
        fixed_pin_site[{x, y}] = pin_id;
    }

    num_cells = num_components - num_pins;

    for (int i = 0; i < num_cells; i++) {
        int cell_id;
        string type_string;

        file >> cell_id;
        file >> type_string;

        int type = type_string[1] - '0';

        cell_type[cell_id] = type;
        cell_ids.push_back(cell_id);
        is_cell[cell_id] = true;
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
    for (int y = 1; y < rows - 1; y++) {
        for (int x = 1; x < cols - 1; x++) {
            int type = get_site_type(x, y);
            legal_sites[type].push_back({x, y});
        }
    }
}

int get_cell_connectivity_score(int cell_id) {
    int score = 0;

    for (int net_id : component_to_nets[cell_id]) {
        int net_size = nets[net_id].size();

        score += net_size;

        for (int component_id : nets[net_id]) {
            if (is_pin[component_id]) {
                score += 30;
            }

            if (is_cell[component_id] && component_id != cell_id) {
                score += 5;
            }
        }
    }

    return score;
}

pair<double, double> get_initial_target_position(int cell_id, vector<bool>& component_is_placed) {
    double total_x = 0.0;
    double total_y = 0.0;
    double total_weight = 0.0;

    for (int net_id : component_to_nets[cell_id]) {
        int net_size = nets[net_id].size();

        double base_weight = 1.0 / max(1, net_size - 1);

        for (int component_id : nets[net_id]) {
            if (component_id == cell_id) {
                continue;
            }

            if (component_is_placed[component_id]) {
                double weight = base_weight;

                if (is_pin[component_id]) {
                    weight *= 4.0;
                }

                total_x += weight * placement[component_id].first;
                total_y += weight * placement[component_id].second;
                total_weight += weight;
            }
        }
    }

    if (total_weight > 0.0) {
        return {total_x / total_weight, total_y / total_weight};
    }

    return {(cols - 1) / 2.0, (rows - 1) / 2.0};
}

pair<double, double> get_current_target_position(int cell_id) {
    double total_x = 0.0;
    double total_y = 0.0;
    double total_weight = 0.0;

    for (int net_id : component_to_nets[cell_id]) {
        int net_size = nets[net_id].size();

        double base_weight = 1.0 / max(1, net_size - 1);

        for (int component_id : nets[net_id]) {
            if (component_id == cell_id) {
                continue;
            }

            double weight = base_weight;

            if (is_pin[component_id]) {
                weight *= 4.0;
            }

            total_x += weight * placement[component_id].first;
            total_y += weight * placement[component_id].second;
            total_weight += weight;
        }
    }

    if (total_weight > 0.0) {
        return {total_x / total_weight, total_y / total_weight};
    }

    return {(cols - 1) / 2.0, (rows - 1) / 2.0};
}

pair<int, int> find_nearest_free_legal_site(int type, pair<double, double> target) {
    double best_distance = 1e100;
    pair<int, int> best_site = {-1, -1};

    for (pair<int, int> site : legal_sites[type]) {
        if (site_to_cell.count(site)) {
            continue;
        }

        if (fixed_pin_site.count(site)) {
            continue;
        }

        double dx = site.first - target.first;
        double dy = site.second - target.second;
        double distance = dx * dx + dy * dy;

        if (distance < best_distance) {
            best_distance = distance;
            best_site = site;
        }
    }

    return best_site;
}

vector<pair<int, int>> get_near_target_sites(
    int type,
    pair<double, double> target,
    pair<int, int> old_pos,
    int limit
) {
    vector<pair<double, pair<int, int>>> scored_sites;

    for (pair<int, int> site : legal_sites[type]) {
        if (site == old_pos) {
            continue;
        }

        if (fixed_pin_site.count(site)) {
            continue;
        }

        double dx = site.first - target.first;
        double dy = site.second - target.second;
        double distance = dx * dx + dy * dy;

        scored_sites.push_back({distance, site});
    }

    sort(
        scored_sites.begin(),
        scored_sites.end(),
        [](const pair<double, pair<int, int>>& a, const pair<double, pair<int, int>>& b) {
            return a.first < b.first;
        }
    );

    vector<pair<int, int>> result;

    int count = min(limit, (int)scored_sites.size());

    for (int i = 0; i < count; i++) {
        result.push_back(scored_sites[i].second);
    }

    return result;
}

pair<int, int> choose_near_target_site(
    int type,
    pair<double, double> target,
    pair<int, int> old_pos
) {
    vector<pair<int, int>> candidates = get_near_target_sites(type, target, old_pos, 30);

    if (candidates.empty()) {
        return old_pos;
    }

    return candidates[get_random_index(candidates.size())];
}

pair<int, int> choose_random_legal_site(int type, pair<int, int> old_pos) {
    for (int attempt = 0; attempt < 100; attempt++) {
        pair<int, int> site = legal_sites[type][get_random_index(legal_sites[type].size())];

        if (site == old_pos) {
            continue;
        }

        if (fixed_pin_site.count(site)) {
            continue;
        }

        return site;
    }

    return old_pos;
}

void make_initial_placement() {
    site_to_cell.clear();

    vector<bool> component_is_placed(num_components, false);

    for (int pin_id : pin_ids) {
        component_is_placed[pin_id] = true;
    }

    vector<int> ordered_cells = cell_ids;

    sort(
        ordered_cells.begin(),
        ordered_cells.end(),
        [](int a, int b) {
            int score_a = get_cell_connectivity_score(a);
            int score_b = get_cell_connectivity_score(b);

            if (score_a != score_b) {
                return score_a > score_b;
            }

            return a < b;
        }
    );

    for (int cell_id : ordered_cells) {
        int type = cell_type[cell_id];

        pair<double, double> target = get_initial_target_position(cell_id, component_is_placed);

        pair<int, int> chosen_site = find_nearest_free_legal_site(type, target);

        if (chosen_site.first == -1) {
            cout << "ERROR: No legal site available for cell " << cell_id << endl;
            exit(1);
        }

        placement[cell_id] = chosen_site;
        site_to_cell[chosen_site] = cell_id;
        component_is_placed[cell_id] = true;
    }
}

void build_site_to_cell() {
    site_to_cell.clear();

    for (int cell_id : cell_ids) {
        site_to_cell[placement[cell_id]] = cell_id;
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

int calculate_total_hpwl() {
    int total = 0;

    for (int net_id = 0; net_id < num_nets; net_id++) {
        total += calculate_net_hpwl(net_id);
    }

    return total;
}

vector<int> get_affected_net_ids(vector<int>& changed_cells) {
    vector<int> affected_net_ids;

    for (int cell_id : changed_cells) {
        for (int net_id : component_to_nets[cell_id]) {
            if (!affected_flag[net_id]) {
                affected_flag[net_id] = true;
                affected_net_ids.push_back(net_id);
            }
        }
    }

    for (int net_id : affected_net_ids) {
        affected_flag[net_id] = false;
    }

    return affected_net_ids;
}

int calculate_affected_hpwl(vector<int>& affected_net_ids) {
    int total = 0;

    for (int net_id : affected_net_ids) {
        total += calculate_net_hpwl(net_id);
    }

    return total;
}

void apply_move(
    int first_cell,
    pair<int, int> old_pos,
    pair<int, int> new_pos,
    int cell_on_site
) {
    placement[first_cell] = new_pos;
    site_to_cell[new_pos] = first_cell;

    if (cell_on_site != -1) {
        placement[cell_on_site] = old_pos;
        site_to_cell[old_pos] = cell_on_site;
    } else {
        site_to_cell.erase(old_pos);
    }
}

void undo_move(
    int first_cell,
    pair<int, int> old_pos,
    pair<int, int> new_pos,
    int cell_on_site
) {
    apply_move(
        first_cell,
        new_pos,
        old_pos,
        cell_on_site
    );
}

int get_cell_on_site(pair<int, int> pos) {
    auto it = site_to_cell.find(pos);

    if (it == site_to_cell.end()) {
        return -1;
    }

    return it->second;
}

int calculate_move_delta(int first_cell, pair<int, int> new_pos) {
    pair<int, int> old_pos = placement[first_cell];

    if (new_pos == old_pos) {
        return 0;
    }

    int cell_on_site = get_cell_on_site(new_pos);

    if (cell_on_site == first_cell) {
        return 0;
    }

    vector<int> changed_cells;

    changed_cells.push_back(first_cell);

    if (cell_on_site != -1) {
        changed_cells.push_back(cell_on_site);
    }

    vector<int> affected_net_ids = get_affected_net_ids(changed_cells);

    int old_affected_cost = calculate_affected_hpwl(affected_net_ids);

    apply_move(
        first_cell,
        old_pos,
        new_pos,
        cell_on_site
    );

    int new_affected_cost = calculate_affected_hpwl(affected_net_ids);

    undo_move(
        first_cell,
        old_pos,
        new_pos,
        cell_on_site
    );

    return new_affected_cost - old_affected_cost;
}

void pick_move(
    int& first_cell,
    pair<int, int>& old_pos,
    pair<int, int>& new_pos,
    int& cell_on_site
) {
    uniform_real_distribution<double> move_choice(0.0, 1.0);

    first_cell = cell_ids[get_random_index(cell_ids.size())];

    int type = cell_type[first_cell];

    old_pos = placement[first_cell];

    if (move_choice(rng) < 0.75) {
        pair<double, double> target = get_current_target_position(first_cell);
        new_pos = choose_near_target_site(type, target, old_pos);
    } else {
        new_pos = choose_random_legal_site(type, old_pos);
    }

    cell_on_site = get_cell_on_site(new_pos);
}

int greedy_polish(int current_cost) {
    vector<int> ordered_cells = cell_ids;

    sort(
        ordered_cells.begin(),
        ordered_cells.end(),
        [](int a, int b) {
            int score_a = get_cell_connectivity_score(a);
            int score_b = get_cell_connectivity_score(b);

            if (score_a != score_b) {
                return score_a > score_b;
            }

            return a < b;
        }
    );

    for (int pass = 0; pass < 5; pass++) {
        bool improved = false;

        for (int cell_id : ordered_cells) {
            int type = cell_type[cell_id];

            pair<int, int> old_pos = placement[cell_id];

            pair<double, double> target = get_current_target_position(cell_id);

            vector<pair<int, int>> candidates = get_near_target_sites(
                type,
                target,
                old_pos,
                20
            );

            int best_delta = 0;
            pair<int, int> best_site = old_pos;

            for (pair<int, int> candidate_site : candidates) {
                int delta = calculate_move_delta(cell_id, candidate_site);

                if (delta < best_delta) {
                    best_delta = delta;
                    best_site = candidate_site;
                }
            }

            if (best_delta < 0) {
                int cell_on_site = get_cell_on_site(best_site);

                apply_move(
                    cell_id,
                    old_pos,
                    best_site,
                    cell_on_site
                );

                current_cost += best_delta;
                improved = true;
            }
        }

        if (!improved) {
            break;
        }
    }

    return current_cost;
}

int run_sa(int total_hpwl) {
    int current_cost = total_hpwl;
    int best_cost = current_cost;

    vector<pair<int, int>> best_placement = placement;

    double temperature = 10.0 * total_hpwl;
    double final_temperature = (5e-5 * total_hpwl) / num_nets;

    uniform_real_distribution<double> probability(0.0, 1.0);

    while (temperature > final_temperature) {
        int moves_per_temperature = 40 * num_cells;

        for (int iteration = 0; iteration < moves_per_temperature; iteration++) {
            int first_cell;
            pair<int, int> old_pos;
            pair<int, int> new_pos;
            int cell_on_site;

            pick_move(
                first_cell,
                old_pos,
                new_pos,
                cell_on_site
            );

            if (new_pos == old_pos) {
                continue;
            }

            vector<int> changed_cells;

            changed_cells.push_back(first_cell);

            if (cell_on_site != -1) {
                changed_cells.push_back(cell_on_site);
            }

            vector<int> affected_net_ids = get_affected_net_ids(changed_cells);

            int old_affected_cost = calculate_affected_hpwl(affected_net_ids);

            apply_move(
                first_cell,
                old_pos,
                new_pos,
                cell_on_site
            );

            int new_affected_cost = calculate_affected_hpwl(affected_net_ids);

            int new_cost = current_cost - old_affected_cost + new_affected_cost;

            int cost_change = new_cost - current_cost;

            if (cost_change < 0 || probability(rng) < exp(-cost_change / temperature)) {
                current_cost = new_cost;

                if (current_cost < best_cost) {
                    best_cost = current_cost;
                    best_placement = placement;
                }
            } else {
                undo_move(
                    first_cell,
                    old_pos,
                    new_pos,
                    cell_on_site
                );
            }
        }

        temperature *= 0.97;
    }

    placement = best_placement;

    build_site_to_cell();

    best_cost = greedy_polish(best_cost);

    build_site_to_cell();

    return best_cost;
}

bool verify_placement() {
    unordered_map<pair<int, int>, int, PairHash> seen;

    for (int pin_id : pin_ids) {
        if (placement[pin_id] != original_pin_placement[pin_id]) {
            cout << "ERROR: Pin " << pin_id << " moved" << endl;
            return false;
        }

        seen[placement[pin_id]] = pin_id;
    }

    for (int cell_id : cell_ids) {
        pair<int, int> pos = placement[cell_id];

        if (seen.count(pos)) {
            cout << "ERROR: Cell " << cell_id << " overlaps with component " << seen[pos] << endl;
            return false;
        }

        seen[pos] = cell_id;

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

    affected_flag.resize(num_nets, false);

    make_legal_sites();

    make_initial_placement();

    build_site_to_cell();

    cout << "Initial net-aware placement check:" << endl;
    verify_placement();

    int total_hpwl = calculate_total_hpwl();

    int best_cost = run_sa(total_hpwl);

    cout << "Final placement check:" << endl;
    verify_placement();

    int final_real_hpwl = calculate_total_hpwl();

    cout << "Input file: " << filename << endl;
    cout << "Number of components: " << num_components << endl;
    cout << "Number of nets: " << num_nets << endl;
    cout << "Grid rows: " << rows << endl;
    cout << "Grid cols: " << cols << endl;
    cout << "Number of pins: " << num_pins << endl;
    cout << "Number of movable cells: " << num_cells << endl;
    cout << "Initial net-aware HPWL: " << total_hpwl << endl;
    cout << "Final best HPWL: " << best_cost << endl;
    cout << "Verified final HPWL: " << final_real_hpwl << endl;

    return 0;
}
