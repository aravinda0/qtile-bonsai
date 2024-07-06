import abc
import collections
from pathlib import Path

import jinja2

from qtile_bonsai.core.nodes import Node, Pane, SplitContainer, Tab
from qtile_bonsai.core.tree import Tree
from qtile_bonsai.core.utils import to_snake_case


jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"), autoescape=True
)

index_tmpl_path = Path("visual_guide/index.template.html")
index_html_path = Path("static/visual_guide/index.html")

_examples_registry: list[type["Example"]] = []


class ExamplePane(Pane):
    label: str
    focused: bool
    min_size: int = 10


class ExampleTree(Tree):
    """Tree variant with helpers for generating visual guide docs.

    Additional dynamic node attributes:
        Node:
            - selected: bool
        Pane:
            See `ExamplePane` above.

    Notes:
        The examples primarily use all the functionality from the core Tree class to
        generate examples. Except for a few things.

        The container-selection mode is a UI-driven feature implemented in the qtile
        layer, outside the core Tree. So we kind of fake its behavior in a simple manner
        here. Same goes for `focus_nth_tab()`/`focus_nth_window()`
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.command: str | None = None
        self.selection: Node | None = None
        self._pane_label_seq = "A"

    def focus(self, pane: ExamplePane):
        super().focus(pane)
        for p in self.iter_panes():
            p.focused = False
        pane.focused = True

    def activate_selection(self, node: Node):
        for n in self.iter_walk():
            n.selected = False
        node.selected = True

    def create_pane(self, *args, **kwargs) -> ExamplePane:
        p = super().create_pane(*args, **kwargs)
        ep = ExamplePane(
            p.principal_rect,
            margin=p.box.margin,
            border=p.box.border,
            padding=p.box.padding,
        )
        ep.id = p.id
        ep.label = self._get_next_pane_label()
        self.focus(ep)
        return ep

    def clone(self) -> "ExampleTree":
        Node.reset_id_seq()
        return super().clone()

    def _get_next_pane_label(self):
        label = self._pane_label_seq
        self._pane_label_seq = chr(ord(self._pane_label_seq) + 1)
        return label


def make_tree():
    Node.reset_id_seq()
    tree = ExampleTree(300, 200)
    tree.set_config("tab_bar.hide_when", "single_tab")
    tree.set_config("tab_bar.height", 15)
    return tree


class Example(metaclass=abc.ABCMeta):
    section: str = ""
    template_path: str = "visual_guide/examples/1_to_n.template.html"

    @abc.abstractmethod
    def build_context_fragment(self) -> dict:
        pass

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls not in _examples_registry:
            _examples_registry.append(cls)

    @classmethod
    def id(cls):
        return to_snake_case(cls.__name__.partition("Eg")[2])

    def build_context(self) -> dict:
        cxt = {
            "id": self.id(),
            "template_path": self.template_path,
        }
        cxt.update(self.build_context_fragment())
        return cxt


class EgSplits1(Example):
    section = "Splits"

    def build_context_fragment(self):
        lhs = make_tree()
        lhs.tab()

        rhs1 = lhs.clone()
        rhs1.split(rhs1.node(4), "x")
        rhs1.command = 'spawn_split(program, "x")'

        rhs2 = lhs.clone()
        rhs2.split(rhs2.node(4), "y")
        rhs2.command = 'spawn_split(program, "y")'

        return {
            "lhs": lhs,
            "rhs_items": [rhs1, rhs2],
        }


class EgTabs1(Example):
    section = "Tabs"

    def build_context_fragment(self):
        lhs = make_tree()
        lhs.tab()

        rhs = lhs.clone()
        rhs.tab()
        rhs.command = "spawn_tab(program)"

        return {
            "lhs": lhs,
            "rhs_items": [rhs],
        }


class EgTabs2(Example):
    section = "Tabs"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x")
        lp3 = lhs.split(lp2, "y")

        rhs = lhs.clone()
        rhs.tab(rhs.node(lp3.id), new_level=True)
        rhs.command = "spawn_tab(program, new_level=True)"

        return {
            "lhs": lhs,
            "rhs_items": [rhs],
        }


class EgTabs3(Example):
    section = "Tabs"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x")
        lp3 = lhs.split(lp2, "y")
        lp4 = lhs.tab(lp3, new_level=True)

        rhs1 = lhs.clone()
        rhs1.tab(rhs1.node(lp4.id))
        rhs1.command = "spawn_tab(program)"

        rhs2 = lhs.clone()
        rhs2.tab(rhs2.node(lp4.id), level=1)
        rhs2.command = "spawn_tab(program, level=1)"

        return {
            "lhs": lhs,
            "rhs_items": [rhs1, rhs2],
        }


class EgMergeToSubtab1(Example):
    section = "Merge to Subtab"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "y")
        lp3 = lhs.split(lp2, "x")
        _ = lhs.split(lp3, "x", normalize=True)
        lhs.focus(lp3)

        rhs1 = lhs.clone()
        rhs1.merge_with_neighbor_to_subtab(rhs1.node(lp3.id), "right", normalize=True)
        rhs1.command = 'merge_to_subtab("right")'
        rhs1.focus(rhs1.node(lp3.id))

        rhs2 = lhs.clone()
        rhs2.merge_with_neighbor_to_subtab(rhs2.node(lp3.id), "left", normalize=True)
        rhs2.command = 'merge_to_subtab("left")'
        rhs2.focus(rhs2.node(lp3.id))

        rhs3 = lhs.clone()
        rhs3.merge_with_neighbor_to_subtab(rhs3.node(lp3.id), "up", normalize=True)
        rhs3.command = 'merge_to_subtab("up")'
        rhs3.focus(rhs3.node(lp3.id))

        return {
            "lhs": lhs,
            "rhs_items": [rhs1, rhs2, rhs3],
        }


class EgMergeToSubtab2(Example):
    section = "Merge to Subtab"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "y")
        lp3 = lhs.split(lp2, "x")
        lp4 = lhs.split(lp3, "x", normalize=True)
        _ = lhs.tab(lp4, new_level=True)
        lhs.focus(lp3)

        rhs1 = lhs.clone()
        rhs1.merge_with_neighbor_to_subtab(rhs1.node(lp3.id), "right", normalize=True)
        rhs1.command = 'merge_to_subtab("right")'
        rhs1.focus(rhs1.node(lp3.id))

        return {
            "lhs": lhs,
            "rhs_items": [rhs1],
        }


class EgPushIn1(Example):
    section = "Push In"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x", ratio=0.33)
        lp3 = lhs.split(lp2, "y")
        lp4 = lhs.split(lp3.parent, "x")
        _ = lhs.split(lp4, "y", ratio=0.3)
        lhs.focus(lp3)

        rhs1 = lhs.clone()
        rhs1.push_in_with_neighbor(
            rhs1.node(lp3.id),
            "right",
            src_selection="mru_deepest",
            dest_selection="mru_largest",
            normalize=True,
        )
        rhs1.command = 'push_in("right")'
        rhs1.focus(rhs1.node(lp3.id))

        rhs2 = lhs.clone()
        rhs2.push_in_with_neighbor(
            rhs2.node(lp3.id),
            "left",
            src_selection="mru_deepest",
            dest_selection="mru_deepest",
        )
        rhs2.command = 'push_in("left")'
        rhs2.focus(rhs2.node(lp3.id))

        return {
            "lhs": lhs,
            "rhs_items": [rhs1, rhs2],
        }


class EgPullOut1(Example):
    section = "Pull Out"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x")
        lp3 = lhs.split(lp2, "y")
        lp4 = lhs.split(lp3, "x")
        lp5 = lhs.split(lp4, "y")
        lhs.focus(lp5)

        rhs1 = lhs.clone()
        rhs1.pull_out(rhs1.node(lp5.id), normalize=True)
        rhs1.focus(rhs1.node(lp5.id))
        rhs1.command = "pull_out()"

        rhs2 = lhs.clone()
        rhs2.pull_out(rhs2.node(lp5.id), position="next", normalize=True)
        rhs2.focus(rhs2.node(lp5.id))
        rhs2.command = 'pull_out(position="next")'

        return {
            "lhs": lhs,
            "rhs_items": [rhs1, rhs2],
        }


class EgPullOut2(Example):
    section = "Pull Out"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x")
        lp3 = lhs.split(lp2, "y")
        lp4 = lhs.split(lp3, "x", ratio=0.33)
        lp5 = lhs.split(lp4, "x")
        lhs.focus(lp5)

        rhs1 = lhs.clone()
        rhs1.pull_out(rhs1.node(lp5.id), normalize=True)
        rhs1.focus(rhs1.node(lp5.id))
        rhs1.command = "pull_out()"

        return {
            "lhs": lhs,
            "rhs_items": [rhs1],
        }


class EgPullOut3(Example):
    section = "Pull Out"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x")
        lp3 = lhs.split(lp2, "y")
        lp4 = lhs.tab(lp3, new_level=True)
        lhs.focus(lp4)

        rhs1 = lhs.clone()
        rhs1.pull_out(rhs1.node(lp4.id), normalize=True)
        rhs1.focus(rhs1.node(lp4.id))
        rhs1.command = "pull_out()"

        return {
            "lhs": lhs,
            "rhs_items": [rhs1],
        }


class EgPullOutToTab1(Example):
    section = "Pull Out to Tab"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x")
        lp3 = lhs.split(lp2, "y")
        lhs.focus(lp3)

        rhs1 = lhs.clone()
        rhs1.pull_out_to_tab(
            rhs1.node(lp3.id),
            normalize=True,
        )
        rhs1.command = "pull_out_to_tab()"
        rhs1.focus(rhs1.node(lp3.id))

        return {
            "lhs": lhs,
            "rhs_items": [rhs1],
        }


class EgPullOutToTab2(Example):
    section = "Pull Out to Tab"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x")
        lp3 = lhs.split(lp2, "y")
        lp4 = lhs.tab(lp3, new_level=True)
        lp5 = lhs.split(lp4, "x")
        lhs.focus(lp5)

        rhs1 = lhs.clone()
        rhs1.pull_out_to_tab(
            rhs1.node(lp5.id),
            normalize=True,
        )
        rhs1.command = "pull_out_to_tab()"
        rhs1.focus(rhs1.node(lp5.id))

        return {
            "lhs": lhs,
            "rhs_items": [rhs1],
        }


class EgPullOutToTab3(Example):
    section = "Pull Out to Tab"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x")
        lp3 = lhs.split(lp2, "y")
        lp4 = lhs.tab(lp3, new_level=True)
        lp5 = lhs.tab(lp4)
        lhs.focus(lp5)

        rhs1 = lhs.clone()
        rhs1.pull_out_to_tab(
            rhs1.node(lp5.id),
            normalize=True,
        )
        rhs1.command = "pull_out_to_tab()"
        rhs1.focus(rhs1.node(lp5.id))

        return {
            "lhs": lhs,
            "rhs_items": [rhs1],
        }


class EgMergeTabs(Example):
    section = "Merge Tabs"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        _ = lhs.split(lp1, "x")
        lp3 = lhs.tab()
        lp4 = lhs.split(lp3, "y")
        lhs.focus(lp4)

        rhs1 = lhs.clone()
        rt1 = rhs1.node(lp1.get_first_ancestor(Tab).id)
        rt2 = rhs1.node(lp4.get_first_ancestor(Tab).id)
        rhs1.merge_tabs(rt2, rt1, "x")
        rhs1.command = 'merge_tabs("previous", "x")'
        rhs1.focus(rhs1.node(lp4.id))

        rhs2 = lhs.clone()
        rt1 = rhs2.node(lp1.get_first_ancestor(Tab).id)
        rt2 = rhs2.node(lp4.get_first_ancestor(Tab).id)
        rhs2.merge_tabs(rt2, rt1, "y")
        rhs2.command = 'merge_tabs("previous", "y")'
        rhs2.focus(rhs2.node(lp4.id))

        return {
            "lhs": lhs,
            "rhs_items": [rhs1, rhs2],
        }


class EgContainerSelectMode1(Example):
    section = "Container Select Mode"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x")
        lp3 = lhs.split(lp2, "y")
        lhs.focus(lp3)

        rhs = lhs.clone()
        rhs.focus(rhs.node(lp3.id))
        rhs.activate_selection(rhs.node(lp3.id))
        rhs.command = "toggle_container_select_mode()"

        return {
            "lhs": lhs,
            "rhs_items": [rhs],
        }


class EgContainerSelectMode2(Example):
    section = "Container Select Mode"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x")
        lp3 = lhs.split(lp2, "y")
        _ = lhs.split(lp3, "x")
        lhs.focus(lp3)
        lhs.activate_selection(lp3.parent)

        rhs1 = lhs.clone()
        rhs1.focus(rhs1.node(lp3.id))
        rhs1.activate_selection(rhs1.node(lp3.parent.parent.id))
        rhs1.command = "select_container_outer()"

        rhs2 = lhs.clone()
        rhs2.focus(rhs2.node(lp3.id))
        rhs2.activate_selection(rhs2.node(lp3.id))
        rhs2.command = "select_container_inner()"

        return {
            "lhs": lhs,
            "rhs_items": [rhs1, rhs2],
        }


class EgContainerSelectMode3(Example):
    section = "Container Select Mode"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x")
        lp3 = lhs.split(lp2, "y")
        _ = lhs.split(lp3, "x")
        lhs.focus(lp3)
        lhs.activate_selection(lp3.parent.parent)

        rhs1 = lhs.clone()
        rhs1.split(rhs1.node(lp3.parent.parent.id), "x", normalize=True)
        rhs1.command = 'spawn_split(program, "x")'

        rhs2 = lhs.clone()
        rhs2.tab(rhs2.node(lp3.parent.parent.id), new_level=True)
        # rhs2.focus(rhs2.node(lp3.id))
        rhs2.command = "spawn_tab(program, new_level=True)"

        return {
            "lhs": lhs,
            "rhs_items": [rhs1, rhs2],
        }


class EgFocusNthTab1(Example):
    section = "Focus nth Tab"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        _ = lhs.tab()
        lp3 = lhs.tab()
        lhs.focus(lp1)

        rhs = lhs.clone()
        rhs.focus(rhs.node(lp3.id))
        rhs.command = "focus_nth_tab(3)"

        return {
            "lhs": lhs,
            "rhs_items": [rhs],
        }


class EgFocusNthTab2(Example):
    section = "Focus nth Tab"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x")
        lp3 = lhs.split(lp2, "y")
        lp4 = lhs.tab(lp3, new_level=True)
        lp5 = lhs.tab(lp4)
        lp6 = lhs.tab(lp1, level=1)
        lhs.focus(lp3)

        rhs1 = lhs.clone()
        rhs1.focus(rhs1.node(lp4.id))
        rhs1.command = "focus_nth_tab(2) / focus_nth_tab(2, level=-1)"

        rhs2 = lhs.clone()
        rhs2.focus(rhs2.node(lp6.id))
        rhs2.command = "focus_nth_tab(2, level=1)"

        return {
            "lhs": lhs,
            "rhs_items": [rhs1, rhs2],
        }


class EgFocusNthWindow1(Example):
    section = "Focus nth Window"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x")
        lp3 = lhs.split(lp2, "y")
        lhs.focus(lp1)

        rhs = lhs.clone()
        rhs.focus(rhs.node(lp3.id))
        rhs.command = "focus_nth_window(3)"

        return {
            "lhs": lhs,
            "rhs_items": [rhs],
        }


class EgFocusNthWindow2(Example):
    section = "Focus nth Window"

    def build_context_fragment(self):
        lhs = make_tree()
        _ = lhs.tab()
        lp2 = lhs.tab()
        lp3 = lhs.split(lp2, "x")
        lp4 = lhs.split(lp3, "y")
        lhs.focus(lp2)

        rhs1 = lhs.clone()
        rhs1.focus(rhs1.node(lp3.id))
        rhs1.command = "focus_nth_window(3)"

        rhs2 = lhs.clone()
        rhs2.focus(rhs2.node(lp4.id))
        rhs2.command = "focus_nth_window(3, ignore_inactive_tabs_at_levels=[1])"

        return {
            "lhs": lhs,
            "rhs_items": [rhs1, rhs2],
        }


class EgFocusNthWindow3(Example):
    section = "Focus nth Window"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x")
        lp3 = lhs.split(lp2, "y")
        lp4 = lhs.tab(lp3, new_level=True)
        lp5 = lhs.tab(lp4)
        _ = lhs.tab(lp1, level=1)
        lhs.focus(lp5)
        lhs.focus(lp1)

        rhs1 = lhs.clone()
        rhs1.focus(rhs1.node(lp3.id))
        rhs1.command = "focus_nth_window(3)"

        rhs2 = lhs.clone()
        rhs2.focus(rhs2.node(lp5.id))
        rhs2.command = "focus_nth_window(3, ignore_inactive_tabs_at_levels=[1,2])"

        return {
            "lhs": lhs,
            "rhs_items": [rhs1, rhs2],
        }


class EgAdvanced1(Example):
    section = "Advanced Options for Container Selection"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "x", ratio=0.33)
        lp3 = lhs.split(lp2, "y", ratio=0.25)
        lp4 = lhs.split(lp3.parent, "x")
        _ = lhs.split(lp4, "y", ratio=0.6)
        lhs.focus(lp3)

        rhs1 = lhs.clone()
        rhs1.merge_with_neighbor_to_subtab(
            rhs1.node(lp3.id),
            "right",
            src_selection="mru_deepest",
            dest_selection="mru_deepest",
        )
        rhs1.command = 'merge_to_subtab(\n    "right",\n    src_selection="mru_deepest",\n    dest_selection="mru_deepest",\n)'
        rhs1.focus(rhs1.node(lp3.id))

        rhs2 = lhs.clone()
        rhs2.merge_with_neighbor_to_subtab(
            rhs2.node(lp3.id),
            "right",
            src_selection="mru_deepest",
            dest_selection="mru_largest",
        )
        rhs2.command = 'merge_to_subtab(\n    "right",\n    src_selection="mru_deepest",\n    dest_selection="mru_largest",\n)'
        rhs2.focus(rhs2.node(lp3.id))

        rhs3 = lhs.clone()
        rhs3.merge_with_neighbor_to_subtab(
            rhs3.node(lp3.id),
            "right",
            src_selection="mru_largest",
            dest_selection="mru_deepest",
        )
        rhs3.command = 'merge_to_subtab(\n    "right",\n    src_selection="mru_largest",\n    dest_selection="mru_deepest",\n)'
        rhs3.focus(rhs3.node(lp3.id))

        rhs4 = lhs.clone()
        rhs4.merge_with_neighbor_to_subtab(
            rhs4.node(lp3.id),
            "right",
            src_selection="mru_largest",
            dest_selection="mru_largest",
        )
        rhs4.command = 'merge_to_subtab(\n    "right",\n    src_selection="mru_largest",\n    dest_selection="mru_largest",\n)'
        rhs4.focus(rhs4.node(lp3.id))

        return {
            "lhs": lhs,
            "rhs_items": [rhs1, rhs2, rhs3, rhs4],
            "subtitle": "Applicable to merge_to_subtab(), push_in(), pull_out()",
        }


class EgAdvanced2(Example):
    section = "Advanced Options for Container Selection"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "y", ratio=0.25)
        lp3 = lhs.split(lp2.parent, "x", ratio=0.33)
        _ = lhs.split(lp3, "y")
        lp5 = lhs.split(lp3.parent, "x")
        lp6 = lhs.tab(lp5, new_level=True)
        _ = lhs.split(lp6, "x")
        lhs.focus(lp3)

        rhs1 = lhs.clone()
        rhs1.merge_with_neighbor_to_subtab(
            rhs1.node(lp3.id),
            "right",
            src_selection="mru_deepest",
            dest_selection="mru_subtab_else_deepest",
        )
        rhs1.focus(rhs1.node(lp3.id))
        rhs1.command = 'merge_to_subtab(\n    "right",\n    dest_selection="mru_subtab_else_deepest",\n)'

        rhs2 = lhs.clone()
        rhs2.merge_with_neighbor_to_subtab(
            rhs2.node(lp3.id),
            "left",
            src_selection="mru_deepest",
            dest_selection="mru_subtab_else_deepest",
        )
        rhs2.focus(rhs2.node(lp3.id))
        rhs2.command = 'merge_to_subtab(\n    "left",\n    dest_selection="mru_subtab_else_deepest",\n)'

        rhs3 = lhs.clone()
        rhs3.merge_with_neighbor_to_subtab(
            rhs3.node(lp3.id),
            "left",
            src_selection="mru_deepest",
            dest_selection="mru_subtab_else_deepest",
        )
        rhs3.focus(rhs2.node(lp3.id))
        rhs3.command = 'merge_to_subtab(\n    "left",\n    dest_selection="mru_subtab_else_deepest",\n)'

        return {
            "lhs": lhs,
            "rhs_items": [rhs1, rhs2],
        }


class EgAdvanced3(Example):
    section = "Advanced Options for Container Selection"

    def build_context_fragment(self):
        lhs = make_tree()
        lp1 = lhs.tab()
        lp2 = lhs.split(lp1, "y", ratio=0.25)
        lp3 = lhs.split(lp2.parent, "x", ratio=0.33)
        _ = lhs.split(lp3, "y")
        lp5 = lhs.split(lp3.parent, "x")
        lp6 = lhs.split(lp5, "y", ratio=0.3)
        _ = lhs.tab(lp6, new_level=True)
        lhs.focus(lp3)

        rhs1 = lhs.clone()
        rhs1.merge_with_neighbor_to_subtab(
            rhs1.node(lp3.id), "right", dest_selection="mru_subtab_else_largest"
        )
        rhs1.focus(rhs1.node(lp3.id))
        rhs1.command = 'merge_to_subtab(\n    "right",\n    dest_selection="mru_subtab_else_largest",\n)'

        rhs2 = lhs.clone()
        rhs2.merge_with_neighbor_to_subtab(
            rhs2.node(lp3.id), "left", dest_selection="mru_subtab_else_largest"
        )
        rhs2.focus(rhs2.node(lp3.id))
        rhs2.command = 'merge_to_subtab(\n    "left",\n    dest_selection="mru_subtab_else_largest",\n)'

        return {
            "lhs": lhs,
            "rhs_items": [rhs1, rhs2],
        }


def main():
    examples = [Eg() for Eg in _examples_registry]

    grouped_examples = collections.defaultdict(list)
    for eg in examples:
        grouped_examples[eg.section].append(eg.build_context())

    index_tmpl = jinja_env.get_template(str(index_tmpl_path))
    index_html = index_tmpl.render({"sections": grouped_examples})

    index_html_path.write_text(index_html)


if __name__ == "__main__":
    main()
