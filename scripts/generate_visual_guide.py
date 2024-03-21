import html
from pathlib import Path

import jinja2

from qtile_bonsai.core.tree import Tree


jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))

tree_templ_path = Path("templates/visual_guide.template.html")
tree_output_path = Path("static/visual_guide/visual_guide.html")


def make_tree():
    tree = Tree(300, 200)
    tree.set_config("tab_bar.hide_when", "single_tab")
    tree.set_config("tab_bar.height", 15)
    return tree


def make_example__splits__1():
    tree_lhs = make_tree()
    tree_lhs.tab()

    tree_rhs = tree_lhs.clone()
    tree_rhs.split(tree_rhs.node(4), "x")

    return {
        "title": "Splits",
        "command": html.escape('split("x")'),
        "lhs": tree_lhs,
        "rhs": tree_rhs,
    }


def make_example__tabs__1():
    tree_lhs = make_tree()
    tree_lhs.tab()

    tree_rhs = tree_lhs.clone()
    tree_rhs.tab()

    return {
        "title": "Tabs",
        "command": html.escape("tab()"),
        "lhs": tree_lhs,
        "rhs": tree_rhs,
    }


def make_example__tabs__2():
    tree_lhs = make_tree()
    lp1 = tree_lhs.tab()
    lp2 = tree_lhs.split(lp1, "x")
    lp3 = tree_lhs.split(lp2, "y")

    tree_rhs = tree_lhs.clone()
    tree_rhs.tab(tree_rhs.node(lp3.id), new_level=True)

    return {
        "title": "Subtabs",
        "command": html.escape("tab(new_level=True)"),
        "lhs": tree_lhs,
        "rhs": tree_rhs,
    }


def make_sections():
    return [
        {
            "title": "Splits",
            "examples": [
                make_example__splits__1(),
            ],
        },
        {
            "title": "Tabs",
            "examples": [
                make_example__tabs__1(),
                make_example__tabs__2(),
            ],
        },
    ]


def main():
    t_tree = jinja_env.get_template("visual_guide.template.html")

    sections = make_sections()
    h_tree = t_tree.render({"sections": sections})

    tree_output_path.write_text(h_tree)


if __name__ == "__main__":
    main()
