# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

from psutil import Process


def modify_terminal_cmd_with_cwd(cmd: str, parent_pid: int) -> str:
    """Tries to modify the provided `cmd` command string such that if it is spawning a
    terminal emulator, then we modify it to open in the same directory as that of the
    provided `parent_pid`.

    This isn't a perfect solution, but works well enough in practice.
    """
    # TODO: Add more terminal emulators. Are there nuances for some terminals that don't
    # have a simple switch?
    terminal_dir_switches = {
        "alacritty": "--working-directory",
        "kitty": "--directory",
    }

    # TODO: Maybe handle things like preceding env var assignments, full program path as
    # cmd.

    cmd_frags = cmd.split(" ")
    program = cmd_frags[0]
    if program in terminal_dir_switches:
        switch = terminal_dir_switches[program]
        if switch not in cmd_frags:
            parent_proc = Process(parent_pid)
            deepest_proc = find_deepest_process(parent_proc)
            return f"{cmd} {switch} {deepest_proc.cwd()}"

    return cmd


def find_deepest_process(process: Process) -> Process:
    """Returns the first process of the deepest tree level from the provided `process`
    tree.
    """

    def _find_deepest_procs(process: Process, level: int = 0) -> list[Process]:
        shell_procs = []

        shell_procs.append((process, level))
        for child in process.children():
            shell_procs.extend(_find_deepest_procs(child, level + 1))

        return shell_procs

    shell_procs = sorted(_find_deepest_procs(process), key=lambda x: x[1], reverse=True)
    return shell_procs[0][0]
