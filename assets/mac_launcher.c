/* Lanzador Finder: ejecuta el script local del mismo bundle, sin Apple Events. */
#include <mach-o/dyld.h>
#include <unistd.h>
#include <libgen.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
int main(void) {
    char executable[PATH_MAX], script[PATH_MAX];
    uint32_t size=sizeof(executable);
    if (_NSGetExecutablePath(executable,&size)!=0) return 1;
    if (snprintf(script,sizeof(script),"%s/../Resources/launch.sh",dirname(executable)) >= sizeof(script)) return 1;
    execl("/bin/bash","bash",script,(char*)0);
    return 1;
}
