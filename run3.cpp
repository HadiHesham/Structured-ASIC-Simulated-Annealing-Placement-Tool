#include <iostream>
#include <vector>
#include <sys/wait.h>
#include <unistd.h>
#include <cstring>
#include <cerrno>

using namespace std;

int main() {
    const int RUNS = 3;
    vector<pid_t> pids(RUNS);

    for (int i = 0; i < RUNS; i++) {
        pid_t pid = fork();

        if (pid == 0) {
            cout.flush();

            execl("./single_placer", "./single_placer", (char*)NULL);

            cerr << "ERROR: execl failed for run " << i + 1 << ": " << strerror(errno) << endl;
            _exit(1);
        }

        if (pid < 0) {
            cerr << "ERROR: fork failed for run " << i + 1 << endl;
            return 1;
        }

        pids[i] = pid;
    }

    for (int i = 0; i < RUNS; i++) {
        waitpid(pids[i], NULL, 0);
    }

    return 0;
}
