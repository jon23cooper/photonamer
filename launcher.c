/*
 * PhotoNamer.app launcher.
 *
 * Compiled into PhotoNamer.app/Contents/MacOS/PhotoNamer by create_app.sh.
 * Resolves the project root (4 levels up from this binary), then exec's
 * the venv Python with main.py — no terminal window appears.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <mach-o/dyld.h>

#define PATHSZ 8192

static void strip_n_components(char *path, int n) {
    char *p = path + strlen(path);
    int count = 0;
    while (p > path) {
        if (*p == '/') {
            if (++count == n) { *(p + 1) = '\0'; return; }
        }
        p--;
    }
}

int main(void) {
    char raw[PATHSZ], resolved[PATHSZ];
    uint32_t sz = PATHSZ;

    if (_NSGetExecutablePath(raw, &sz) != 0) return 1;
    if (!realpath(raw, resolved)) return 1;

    /* resolved = …/photonamer/PhotoNamer.app/Contents/MacOS/PhotoNamer
       strip 4 path components → …/photonamer/                           */
    strip_n_components(resolved, 4);

    char python[PATHSZ], script[PATHSZ], cwd[PATHSZ];
    snprintf(python, PATHSZ, "%s.venv/bin/python", resolved);
    snprintf(script, PATHSZ, "%smain.py",           resolved);
    snprintf(cwd,    PATHSZ, "%s",                  resolved);

    /* drop trailing slash for chdir */
    size_t n = strlen(cwd);
    if (n > 0 && cwd[n - 1] == '/') cwd[n - 1] = '\0';

    chdir(cwd);
    execl(python, python, script, NULL);

    /* exec failed — tell the user */
    char cmd[PATHSZ * 2];
    snprintf(cmd, sizeof(cmd),
        "osascript -e 'display alert \"PhotoNamer\" message "
        "\"Could not start PhotoNamer.\\n\\n"
        "Run setup.sh in the PhotoNamer project folder first.\" as critical'");
    system(cmd);
    return 1;
}
