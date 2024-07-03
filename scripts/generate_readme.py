# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


# pyright: reportPrivateUsage=false


import ast
import inspect
import pathlib

import jinja2
from libqtile.layout.base import Layout
from libqtile.widget.base import _Widget

from qtile_bonsai import Bonsai, BonsaiBar
from qtile_bonsai.core.utils import rewrap


t_readme_path = pathlib.Path("templates/README.template.md")
readme_path = pathlib.Path("README.md")


def main():
    t_readme = jinja2.Template(t_readme_path.read_text())

    readme = t_readme.render(
        {
            "layout_config_options": get_config_options(Bonsai),
            "commands": get_exposed_comands(Bonsai),
            "widget_config_options": get_config_options(BonsaiBar),
        }
    )

    readme_path.write_text(readme)


def get_config_options(qtile_entity_cls) -> list:
    config_options = []

    for option in qtile_entity_cls.options:
        if option.description is None:
            raise ValueError(
                f"The `{option.name}` layout option is missing documentation"
            )

        config_options.append(
            {
                "name": option.name,
                "default": option.default_value_label or option.default_value,
                "description": rewrap(
                    option.description, width=40, dedent=True, html_whitespace=True
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
            (
                d
                for d in node.decorator_list
                if getattr(d, "id", "") == "expose_command"
            ),
            None,
        )
        if expose_command_decorator is not None and node.name not in excluded_commands:
            docstring = ast.get_docstring(node)
            if docstring is None:
                raise ValueError(f"The `{node.name}` command is missing documentation")
            commands.append(
                {
                    "name": node.name,
                    "docstring": rewrap(
                        docstring, width=75, dedent=True, html_whitespace=True
                    ),
                }
            )

    v = ast.NodeVisitor()
    v.visit_FunctionDef = is_exposed_command
    v.visit(ast.parse(inspect.getsource(layout_cls)))

    return commands


if __name__ == "__main__":
    main()
