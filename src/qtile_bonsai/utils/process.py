# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

from libqtile.log_utils import logger
from psutil import Process


def modify_terminal_cmd_with_cwd(cmd: str, parent_pid: int) -> str:
    """Tries to modify the provided `cmd` command string such that if it is spawning a
    terminal emulator, then we modify it to open in the same directory as that of the
    provided `parent_pid`.

    This isn't a perfect solution, but works well enough in practice.
    Looking for the deepest **shell** process to determine cwd seems to work alright for
    now. Just looking for any deepest process fails when something like nvim spawns node
    for LSP and that has the home directory as cwd.
    """
    # TODO: Add more terminal emulators. Are there nuances for some terminals that don't
    # have a simple switch?
    terminal_dir_switches = {
        "alacritty": "--working-directory",
        "kitty": "--directory",
        "gnome-terminal": "--working-directory",
        "urxvt": "-cd",
        "rxvt": "-cd",
    }

    # TODO: Maybe handle things like preceding env var assignments, full program path as
    # cmd.

    cmd_frags = cmd.split(" ")
    terminal_program = cmd_frags[0]
    if terminal_program in terminal_dir_switches:
        switch = terminal_dir_switches[terminal_program]
        if switch not in cmd_frags:
            parent_proc = Process(parent_pid)
            cwd_ref_proc = find_deepest_shell_process(parent_proc) or parent_proc
            try:
                cwd = f"'{cwd_ref_proc.cwd()}'"
            except Exception:
                # Wuss out on any kind of error and just return original command.
                logger.warn("Failed while trying to get cwd of process.")
                return cmd
            return f"{cmd} {switch} {cwd}"

    return cmd


def find_deepest_shell_process(process: Process) -> Process | None:
    """Returns the first shell process found at the deepest tree levels from the
    provided `process` tree or None, if no such process exists.
    """
    shells = {
        "zsh",
        "bash",
        "fish",
        "ksh",
        "sh",
        "csh",
        "tcsh",
    }

    def _find_deepest_shell_procs(process: Process, level: int = 0) -> list[Process]:
        shell_procs = []

        if process.name() in shells:
            shell_procs.append((process, level))
        for child in process.children():
            shell_procs.extend(_find_deepest_shell_procs(child, level + 1))

        return shell_procs

    shell_procs = sorted(
        _find_deepest_shell_procs(process), key=lambda x: x[1], reverse=True
    )
    if not shell_procs:
        return None

    return shell_procs[0][0]
