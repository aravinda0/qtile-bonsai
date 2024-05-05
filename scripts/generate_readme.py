# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


import ast
import inspect
import pathlib

import jinja2
from libqtile.layout.base import Layout

from qtile_bonsai import Bonsai
from qtile_bonsai.core.utils import rewrap


t_readme_path = pathlib.Path("templates/README.template.md")
readme_path = pathlib.Path("README.md")


def main():
    t_readme = jinja2.Template(t_readme_path.read_text())

    config_options = get_config_options(Bonsai)
    commands = get_exposed_comands(Bonsai)

    readme = t_readme.render(
        {
            "config_options": config_options,
            "commands": commands,
        }
    )

    readme_path.write_text(readme)


def get_config_options(layout_cls: type[Layout]) -> list:
    config_options = []

    for option in layout_cls.defaults:
        description = option[2]
        if description is None:
            raise ValueError(f"The `{option[0]}` option is missing documentation")

        config_options.append(
            {
                "name": option[0],
                "default": option[1],
                "description": rewrap(
                    description, width=80, dedent=True, html_whitespace=True
                ),
            }
        )

    return config_options


def get_exposed_comands(layout_cls: type[Layout]) -> list:
    excluded_commands = {
        "info",
    }
    commands = []

    def is_exposed_command(node):
        expose_command_decorator = next(
            (d for d in node.decorator_list if d.id == "expose_command"), None
        )
        if expose_command_decorator is not None and node.name not in excluded_commands:
            docstring = ast.get_docstring(node)
            if docstring is None:
                raise ValueError(f"The `{node.name}` command is missing documentation")
            commands.append(
                {
                    "name": node.name,
                    "docstring": rewrap(
                        docstring, width=85, dedent=True, html_whitespace=True
                    ),
                }
            )

    v = ast.NodeVisitor()
    v.visit_FunctionDef = is_exposed_command
    v.visit(ast.parse(inspect.getsource(layout_cls)))

    return commands


if __name__ == "__main__":
    main()
