# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from __future__ import annotations

import collections
import textwrap
import uuid
from typing import Any, Callable, Iterable, Iterator

from strenum import StrEnum

from qtile_bonsai.core.geometry import (
    Axis,
    AxisParam,
    Direction,
    DirectionParam,
    Rect,
)
from qtile_bonsai.core.nodes import (
    Node,
    Pane,
    SplitContainer,
    Tab,
    TabBar,
    TabContainer,
)
from qtile_bonsai.core.utils import validate_unit_range

_PruningCase = collections.namedtuple("_PruningCase", ("chain", "prune"))


class TreeEvent(StrEnum):
    node_added = "node_added"
    node_removed = "node_removed"


class InvalidTreeStructureError(Exception):
    pass


class Tree:
    TreeEventCallback = Callable[[list[Node]], None]

    _recency_seq = 0

    # Tab levels of trees begin from 1 for the topmost level. Use 'level 0' to store
    # defaults.
    _default_config_level_key = 0

    def __init__(self, width: int, height: int):
        self._width: int = width
        self._height: int = height
        self._config: collections.defaultdict[int, dict] = self.make_default_config()
        self._root: TabContainer | None = None
        self._event_subscribers: collections.defaultdict[
            TreeEvent, dict[str, Tree.TreeEventCallback]
        ] = collections.defaultdict(dict)
        self._pruning_cases = self._get_pruning_cases()

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def root(self) -> TabContainer | None:
        return self._root

    @property
    def is_empty(self) -> bool:
        return self.root is None

    def make_default_config(self) -> collections.defaultdict[int, dict[str, Any]]:
        config = collections.defaultdict(dict)
        config[self._default_config_level_key] = {
            "window.margin": 0,
            "window.border_size": 1,
            "window.padding": 0,
            "tab_bar.height": 20,
            "tab_bar.margin": 0,
            "tab_bar.border_size": 0,
            "tab_bar.padding": 0,
            "tab_bar.hide_when": "never",
        }
        return config

    def set_config(self, key: str, value: Any, *, level: int | None = None):
        level = level if level is not None else self._default_config_level_key
        if level < self._default_config_level_key:
            raise ValueError("`level` must be a positive number")

        self._config[level][key] = value

    def get_config(
        self,
        key: str,
        *,
        level: int | None = None,
        fall_back_to_default: bool = True,
    ) -> Any:
        level = level if level is not None else self._default_config_level_key
        if level < self._default_config_level_key:
            raise ValueError("`level` must be a positive number")

        if fall_back_to_default and (
            level not in self._config or key not in self._config[level]
        ):
            level = self._default_config_level_key

        return self._config[level][key]

    def create_pane(
        self,
        *,
        content_rect: Rect | None = None,
        padding_rect: Rect | None = None,
        border_rect: Rect | None = None,
        margin_rect: Rect | None = None,
        principal_rect: Rect | None = None,
        margin: int | None = None,
        border: int | None = None,
        padding: int | None = None,
        tab_level: int | None = None,
    ) -> Pane:
        """Factory method for creating a new Pane instance.

        Passing `tab_level` allows us to apply appropriate level-based configuration to
        the pane.
        """

        if margin is None:
            margin = self.get_config("window.margin", level=tab_level)
        if border is None:
            border = self.get_config("window.border_size", level=tab_level)
        if padding is None:
            padding = self.get_config("window.padding", level=tab_level)

        return Pane(
            content_rect=content_rect,
            padding_rect=padding_rect,
            border_rect=border_rect,
            margin_rect=margin_rect,
            principal_rect=principal_rect,
            margin=margin,
            border=border,
            padding=padding,
        )

    def create_split_container(self) -> SplitContainer:
        """Factory method for creating a new SplitContainer instance"""
        return SplitContainer()

    def create_tab(self, title: str = "") -> Tab:
        """Factory method for creating a new Tab instance"""
        return Tab(title)

    def create_tab_container(self) -> TabContainer:
        """Factory method for creating a new TabContainer instance"""
        return TabContainer()

    def reset_dimensions(self, width: int, height: int):
        self._width = width
        self._height = height

        # Ensure the tree nodes get resized proportionally
        if self._root is not None:
            self._root.transform(Axis.x, 0, width)
            self._root.transform(Axis.y, 0, height)

    def tab(
        self,
        at_pane: Pane | None = None,
        *,
        new_level: bool = False,
        level: int | None = None,
    ) -> Pane:
        if self.is_empty:
            if at_pane is not None or new_level or level is not None:
                raise ValueError(
                    "The tree is empty. The provided arguments are invalid."
                )

            pane, added_nodes = self._add_very_first_tab()
        elif new_level:
            if at_pane is None:
                raise ValueError(
                    "`new_level` requires a reference `at_pane` under which to add tabs"
                )

            pane, added_nodes = self._add_tab_at_new_level(at_pane)
        elif level is not None:
            if at_pane is None:
                raise ValueError("`level` requires a reference `at_pane`")
            if level < 1:
                raise ValueError("`level` must be 1 or higher")

            ancestor_tab_containers = at_pane.get_ancestors(TabContainer)
            max_tab_level = len(ancestor_tab_containers)
            if level > max_tab_level:
                raise ValueError(
                    f"`{level}` is an invalid level. The tree currently only has "
                    f"{max_tab_level} levels."
                )

            tab_container = ancestor_tab_containers[-level]
            pane, added_nodes = self._add_tab(tab_container)
        else:
            if at_pane is None:
                tab_container = self._root
            else:
                tab_container = at_pane.get_first_ancestor(TabContainer)

            if tab_container is None:
                raise InvalidTreeStructureError

            pane, added_nodes = self._add_tab(tab_container)

        self._notify_subscribers(TreeEvent.node_added, added_nodes)

        return pane

    def split(
        self,
        pane: Pane,
        axis: AxisParam,
        *,
        ratio: float = 0.5,
        normalize: bool = False,
    ) -> Pane:
        """Create a new pane next to the provided pane, adjusting dimensions as
        necessary.

        If `normalize` is provided, it takes precedence over `ratio`. In this case, the
        new pane and all the sibling nodes will be adjusted to be of equal size.
        """
        validate_unit_range(ratio, "ratio")
        axis = Axis(axis)

        added_nodes = []

        pane_container = pane.parent
        pane_index = pane_container.children.index(pane)

        self._maybe_morph_split_container(pane_container, axis)

        p1_rect, p2_rect = pane.principal_rect.split(axis, ratio)
        pane.principal_rect = p1_rect

        # During the flow below, we try to ensure `new_pane` is created after any other
        # new nodes to maintain ID sequence.
        if pane_container.axis == axis:
            new_pane = self.create_pane(
                principal_rect=p2_rect, tab_level=pane.tab_level
            )
            new_pane.parent = pane_container
            pane_container.children.insert(pane_index + 1, new_pane)

            if normalize:
                self.normalize(pane_container)
        else:
            pane_container.children.remove(pane)

            new_split_container = self.create_split_container()
            new_split_container.axis = axis
            new_split_container.parent = pane_container
            pane_container.children.insert(pane_index, new_split_container)
            added_nodes.append(new_split_container)

            pane.parent = new_split_container
            new_split_container.children.append(pane)

            new_pane = self.create_pane(
                principal_rect=p2_rect, tab_level=pane.tab_level
            )
            new_pane.parent = new_split_container
            new_split_container.children.append(new_pane)

        added_nodes.append(new_pane)

        self._notify_subscribers(TreeEvent.node_added, added_nodes)

        return new_pane

    def resize(self, pane: Pane, axis: AxisParam, amount: int):
        axis = Axis(axis)

        super_node = self._find_super_node_to_resize(pane, axis)
        if super_node is None:
            return

        if super_node.is_last_child:
            br1, br2 = super_node.operational_sibling, super_node
        else:
            br1, br2 = super_node, super_node.operational_sibling

        br_shrink = br2 if amount > 0 else br1
        actual_amount = min(abs(amount), br_shrink.shrinkability(axis))
        actual_amount = actual_amount if amount > 0 else -actual_amount

        points = [
            br1.principal_rect.coord(axis),
            br1.principal_rect.coord2(axis) + actual_amount,
            br2.principal_rect.coord2(axis),
        ]

        br1.transform(axis, points[0], points[1] - points[0])
        br2.transform(axis, points[1], points[2] - points[1])

    def normalize(self, node: Node, *, recurse: bool = True):
        def _normalize(node: Node, *, recurse: bool):
            if isinstance(node, SplitContainer):
                per_child_size = round(
                    node.principal_rect.size(node.axis) / len(node.children)
                )
                s = node.principal_rect.coord(node.axis)
                for child in node.children:
                    child.transform(node.axis, s, per_child_size)
                    s += per_child_size
            if recurse:
                for child in node.children:
                    _normalize(child, recurse=recurse)

        _normalize(node, recurse=recurse)

    def remove(self, pane: Pane, *, normalize: bool = False) -> Pane | None:
        removed_nodes = []

        br_remove, br_remove_nodes = self._find_removal_branch(pane)
        removed_nodes.extend(br_remove_nodes)

        if br_remove is self._root:
            self._root = None
            self._notify_subscribers(TreeEvent.node_removed, removed_nodes)
            return None

        assert br_remove.parent is not None
        assert br_remove.operational_sibling is not None

        container = br_remove.parent
        br_sibling = br_remove.operational_sibling
        container.children.remove(br_remove)

        if isinstance(container, SplitContainer):
            # Space redistribution is applicable. Give space to sibling node.
            br_remove_rect = br_remove.principal_rect
            br_sibling_rect = br_sibling.principal_rect
            axis = container.axis
            start = min(br_remove_rect.coord(axis), br_sibling_rect.coord(axis))
            br_sibling.transform(
                axis, start, br_sibling_rect.size(axis) + br_remove_rect.size(axis)
            )
            if normalize:
                self.normalize(container)

        removed_nodes.extend(self._do_post_removal_pruning(br_sibling))

        self._notify_subscribers(TreeEvent.node_removed, removed_nodes)

        return self._pick_mru_pane(self.iter_panes(start=br_sibling))

    def focus(self, pane: Pane):
        """Ensures the provided `pane` is visible by activating all ancestor tabs.

        For the moment, we don't actually maintain the focused node internally, which
        aligns with usage alongside extrnal window managers that control the notion of
        focus.
        """
        node = pane
        while node.parent is not None:
            if isinstance(node, Tab):
                node.parent.active_child = node
            node = node.parent
        pane.recency = self.next_recency_value()

    def left(self, pane: Pane, *, wrap: bool = True) -> Pane:
        adjacent = self.find_adjacent_panes(pane, "left", wrap=wrap)
        if not adjacent:
            return pane
        return self._pick_mru_pane(adjacent)

    def right(self, pane: Pane, *, wrap: bool = True) -> Pane:
        adjacent = self.find_adjacent_panes(pane, "right", wrap=wrap)
        if not adjacent:
            return pane
        return self._pick_mru_pane(adjacent)

    def up(self, pane: Pane, *, wrap: bool = True) -> Pane:
        adjacent = self.find_adjacent_panes(pane, "up", wrap=wrap)
        if not adjacent:
            return pane
        return self._pick_mru_pane(adjacent)

    def down(self, pane: Pane, *, wrap: bool = True) -> Pane:
        adjacent = self.find_adjacent_panes(pane, "down", wrap=wrap)
        if not adjacent:
            return pane
        return self._pick_mru_pane(adjacent)

    def next_tab(self, node: Node, *, wrap: bool = True) -> Pane | None:
        return self._next_tab(node, 1, wrap=wrap)

    def prev_tab(self, node: Node, *, wrap: bool = True) -> Pane | None:
        return self._next_tab(node, -1, wrap=wrap)

    def swap(self, p1: Pane, p2: Pane):
        """Swaps the two panes provided in the tree. Their geometries are modified so
        that the overall tree geometry remains the same.
        """
        sc1 = p1.parent
        p1_index = sc1.children.index(p1)

        sc2 = p2.parent
        p2_index = sc2.children.index(p2)

        p1.parent, p2.parent = p2.parent, p1.parent
        sc1.children[p1_index], sc2.children[p2_index] = (
            sc2.children[p2_index],
            sc1.children[p1_index],
        )

        # Swap geometries
        p1.box, p2.box = p2.box, p1.box

    def swap_tabs(self, t1: Tab, t2: Tab):
        """Swaps the two tabs provided in the tree and adjusts geometries as needed. The
        provided tabs must not be nested under one another.
        """
        if t1 in t2.get_ancestors() or t2 in t1.get_ancestors():
            raise ValueError(
                "`t1` and `t2` must be independent tabs such that one is not nested "
                "under the other"
            )

        tc1 = t1.parent
        t1_index = tc1.children.index(t1)
        t1_rect = Rect.from_rect(t1.principal_rect)

        tc2 = t2.parent
        t2_index = tc2.children.index(t2)
        t2_rect = Rect.from_rect(t2.principal_rect)

        t1.parent, t2.parent = t2.parent, t1.parent
        tc1.children[t1_index], tc2.children[t2_index] = (
            tc2.children[t2_index],
            tc1.children[t1_index],
        )

        if tc1 is not tc2:
            t1.transform(Axis.x, t2_rect.x, t2_rect.w)
            t1.transform(Axis.y, t2_rect.y, t2_rect.h)
            t2.transform(Axis.x, t1_rect.x, t1_rect.w)
            t2.transform(Axis.y, t1_rect.y, t1_rect.h)

    def is_visible(self, node: Node) -> bool:
        """Whether a node is visible or not. A node is visible if all its ancestor
        tabs are active.
        """
        n = node
        while n.parent is not None:
            if isinstance(n.parent, TabContainer) and n.parent.active_child is not n:
                return False
            n = n.parent
        return True

    def find_adjacent_panes(
        self, pane: Pane, direction: DirectionParam, *, wrap: bool = True
    ) -> list[Pane]:
        """Returns all panes that are adjacent to the provided `pane` in the specified
        `direction`.

        NOTES:
            - 'Adjacent' here means that two panes may partially or wholly share a
                border.
            - A pane is not adjacent to itself.
            - Any tab bars of sub-tab levels that are in between two panes are ignored.
        """
        direction = Direction(direction)

        super_node = self._find_oriented_border_encompassing_super_node(pane, direction)
        if super_node is None:
            return []

        super_node_sibling = super_node.sibling(direction.axis_unit, wrap=wrap)
        if super_node_sibling is None or super_node_sibling is super_node:
            return []

        adjacent = []
        inv_axis = direction.axis.inv
        for candidate in self._find_panes_along_border(super_node_sibling, direction):
            coord1_ok = candidate.principal_rect.coord(
                inv_axis
            ) < pane.principal_rect.coord2(inv_axis)
            coord2_ok = candidate.principal_rect.coord2(
                inv_axis
            ) > pane.principal_rect.coord(inv_axis)
            if coord1_ok and coord2_ok:
                adjacent.append(candidate)

        return adjacent

    def iter_walk(
        self, start: Node | None = None, *, only_visible: bool = False
    ) -> Iterator[Node]:
        if self.is_empty:
            return

        def walk(node) -> Iterator[Node]:
            yield node
            if only_visible and isinstance(node, TabContainer):
                yield from walk(node.active_child)
            else:
                for n in node.children:
                    yield from walk(n)

        yield from walk(start or self._root)

    def iter_panes(
        self, visible: bool | None = None, start: Node | None = None
    ) -> Iterator[Pane]:
        if self.is_empty:
            return

        for node in self.iter_walk(start):
            if isinstance(node, Pane):
                if visible is not None:
                    if self.is_visible(node) == visible:
                        yield node
                else:
                    yield node

    def subscribe(self, event: TreeEvent, callback: Tree.TreeEventCallback) -> str:
        subscription_id = uuid.uuid4().hex
        self._event_subscribers[event][subscription_id] = callback
        return subscription_id

    def unsubscribe(self, subscription_id: str):
        for subscribers in self._event_subscribers.values():
            if subscription_id in subscribers:
                del subscribers[subscription_id]
                return

    @classmethod
    def next_recency_value(cls):
        cls._recency_seq += 1
        return cls._recency_seq

    def __repr__(self) -> str:
        if self.is_empty:
            return "<empty>"

        def walk(node, prefix=""):
            frags = [f"{prefix}- {repr(node)}"]
            for n in node.children:
                frags.extend(walk(n, prefix + 4 * " "))
            return frags

        return "\n".join(walk(self._root))

    def _get_pruning_cases(self) -> list[_PruningCase]:
        return [
            _PruningCase(
                chain=(SplitContainer, SplitContainer, Pane), prune=self._prune_sc_sc_p
            ),
            _PruningCase(
                chain=(Tab, SplitContainer, SplitContainer), prune=self._prune_t_sc_sc
            ),
            _PruningCase(
                chain=(SplitContainer, SplitContainer, SplitContainer),
                prune=self._prune_sc_sc_sc,
            ),
            _PruningCase(
                chain=(SplitContainer, SplitContainer, TabContainer),
                prune=self._prune_sc_sc_tc,
            ),
            _PruningCase(
                chain=(SplitContainer, TabContainer, Tab),
                prune=self._prune_sc_tc_t,
            ),
            _PruningCase(
                chain=(type(None), TabContainer, Tab),
                prune=self._prune_none_tc_t,
            ),
        ]

    def _add_very_first_tab(self) -> tuple[Pane, list[Node]]:
        """Add the first tab and its pane on an empty tree. A special case where the
        root is set and initial rects are set for use by all subsequent tabs and panes.
        """
        added_nodes = []

        top_level = 1
        tab_container = self.create_tab_container()
        tab_container.tab_bar = self._build_tab_bar(0, 0, self.width, top_level, 1)

        added_nodes.append(tab_container)

        new_tab = self.create_tab()
        new_tab.parent = tab_container
        tab_container.children.append(new_tab)
        tab_container.active_child = new_tab
        added_nodes.append(new_tab)

        new_split_container = self.create_split_container()
        new_split_container.parent = new_tab
        new_tab.children.append(new_split_container)
        added_nodes.append(new_split_container)

        # Max sized rect, allowing for top level tab bar
        tab_bar_rect = tab_container.tab_bar.box.principal_rect
        new_pane_rect = Rect(
            0, tab_bar_rect.y2, self.width, self.height - tab_bar_rect.h
        )

        new_pane = self.create_pane(principal_rect=new_pane_rect, tab_level=top_level)
        new_pane.parent = new_split_container
        new_split_container.children.append(new_pane)
        added_nodes.append(new_pane)

        self._root = tab_container

        return new_pane, added_nodes

    def _add_tab(self, tab_container: TabContainer) -> tuple[Pane, list[Node]]:
        added_nodes = []

        self._maybe_restore_tab_bar(tab_container)

        new_tab = self.create_tab()
        new_tab.parent = tab_container
        tab_container.children.append(new_tab)
        added_nodes.append(new_tab)

        new_split_container = self.create_split_container()
        new_split_container.parent = new_tab
        new_tab.children.append(new_split_container)
        added_nodes.append(new_split_container)

        new_pane_rect = tab_container.get_inner_rect()

        new_pane = self.create_pane(
            principal_rect=new_pane_rect, tab_level=tab_container.tab_level
        )
        new_pane.parent = new_split_container
        new_split_container.children.append(new_pane)
        added_nodes.append(new_pane)

        return new_pane, added_nodes

    def _add_tab_at_new_level(self, at_pane: Pane) -> tuple[Pane, list[Node]]:
        """Converts the provided `at_pane` into a subtab tree, placing `at_pane` as the
        first tab in the new level, and creates a new second tab in that subtab tree.
        """
        added_nodes = []

        at_split_container = at_pane.parent
        if at_split_container is None:
            raise InvalidTreeStructureError

        # Remove `at_pane` from tree so we can begin to insert a new tab container
        # subtree. We add it back later as a leaf under the new subtree.
        at_pane_pos = at_split_container.children.index(at_pane)
        at_split_container.children.remove(at_pane)

        new_tab_container = self.create_tab_container()
        new_tab_container.parent = at_split_container
        at_split_container.children.insert(at_pane_pos, new_tab_container)
        added_nodes.append(new_tab_container)

        new_tab_level = at_pane.tab_level + 1
        new_tab_container.tab_bar = self._build_tab_bar(
            at_pane.principal_rect.x,
            at_pane.principal_rect.y,
            at_pane.principal_rect.w,
            new_tab_level,
            2,
        )

        tab1 = self.create_tab()
        tab1.parent = new_tab_container
        new_tab_container.children.append(tab1)

        split_container1 = self.create_split_container()
        split_container1.parent = tab1
        tab1.children.append(split_container1)

        # Attach `at_pane` under the first tab of our new subtree.
        at_pane.parent = split_container1
        split_container1.children.append(at_pane)

        # Adjust `at_pane's` dimensions to account for the new tab bar
        at_pane_rect = at_pane.principal_rect
        at_pane_rect.y = new_tab_container.tab_bar.box.principal_rect.y2
        at_pane_rect.h -= new_tab_container.tab_bar.box.principal_rect.h
        at_pane.box.principal_rect = at_pane_rect

        # `at_pane` is now at tab_level = n + 1. We modify properties to align
        # with n + 1 level config.
        at_pane.box.margin = self.get_config("window.margin", level=new_tab_level)
        at_pane.box.border = self.get_config("window.border_size", level=new_tab_level)
        at_pane.box.padding = self.get_config("window.padding", level=new_tab_level)

        # Start adding the real new tab that was requested and mark it as the active
        # tab.
        tab2 = self.create_tab()
        tab2.parent = new_tab_container
        new_tab_container.children.append(tab2)
        new_tab_container.active_child = tab2
        added_nodes.append(tab2)

        split_container2 = self.create_split_container()
        split_container2.parent = tab2
        tab2.children.append(split_container2)
        added_nodes.append(split_container2)

        # The new tab's pane will have the same dimensions as `at_pane` after it was
        # adjusted above.
        new_pane = self.create_pane(
            principal_rect=at_pane.principal_rect, tab_level=new_tab_level
        )
        new_pane.parent = split_container2
        split_container2.children.append(new_pane)
        added_nodes.append(new_pane)

        return new_pane, added_nodes

    def _build_tab_bar(
        self, x: int, y: int, w: int, tab_level: int, tab_count: int
    ) -> TabBar:
        bar_height = self.get_config("tab_bar.height", level=tab_level)

        # hide the tab bar when relevant, by setting its height to 0
        bar_hide_when = self.get_config("tab_bar.hide_when", level=tab_level)
        if bar_hide_when == "always" or (
            bar_hide_when == "single_tab" and tab_count == 1
        ):
            bar_height = 0

        return TabBar(
            principal_rect=Rect(x, y, w, bar_height),
            margin=self.get_config("tab_bar.margin", level=tab_level),
            border=self.get_config("tab_bar.border_size", level=tab_level),
            padding=self.get_config("tab_bar.padding", level=tab_level),
        )

    def _maybe_restore_tab_bar(self, tab_container: TabContainer):
        """Depending on the `tab_bar.hide_when` config, we may require that a tab bar
        that was previously hidden be made visible again.
        """
        if len(tab_container.children) > 2:
            # If tab bar restoration was required, we'd have already done it when the
            # 2nd tab was added.
            return

        tab_level = tab_container.tab_level
        bar_hide_when = self.get_config("tab_bar.hide_when", level=tab_level)
        bar_rect = tab_container.tab_bar.box.principal_rect
        if bar_hide_when != "always" and bar_rect.h == 0:
            bar_height = self.get_config("tab_bar.height", level=tab_level)
            bar_rect.h = bar_height

            # We need to adjust the contents of the first tab after the bar takes up its
            # space.
            first_tab = tab_container._children[0]
            first_tab.transform(
                Axis.y, bar_rect.y2, first_tab.principal_rect.h - bar_height
            )

    def _maybe_morph_split_container(
        self, split_container: SplitContainer, requested_axis
    ):
        if (
            split_container.axis != requested_axis
            and split_container.is_nearest_under_tab_container
            and split_container.has_single_child
        ):
            split_container.axis = requested_axis

    def _find_removal_branch(self, pane: Pane) -> tuple[Node, list[Node]]:
        n = pane
        nodes_to_remove: list[Node] = [n]
        while n is not self._root and n.is_sole_child:
            n = n.parent
            nodes_to_remove.append(n)
        return n, nodes_to_remove

    def _do_post_removal_pruning(self, node: Node) -> list[Node]:
        """After a removal operation, optimizes the tree to keep it minimal by
        discarding nodes that are now unnecessary to keep the same semantic tree.

        This arises when the provided `node` is now a sole remnant child wrt its parent.
        We take `node` and look at its two ancestors, `n2` and `n1`, giving us a
        top-down chain of `[n1, n2, n3]`.

        We then look for opportunities to merge `n3` or its children into `n1` and
        discard whatever nodes we can. The tree configuration options can also play a
        role in determining whether or not pruning happens.

        All the `[n1, n2, n3]` possibilities are listed below.
        The arrows point to the parent node. The chains that are prunable are marked
        with *.

            T ◄─┐
                │
                ├── SC ◄───── P
                │
          *SC ◄─┘

           TC ◄────  T ◄───┐
                           ├─ SC
                           │
           *T ◄──┬─ SC ◄───┘
                 │
                 │
          *SC ◄──┘

          *SC ◄─┐
                │
                ├── TC ◄────── T
                │
        *None ◄─┘

            T ◄─┐
                │
                ├── SC ◄────── TC
                │
          *SC ◄─┘


        Note that the case of `TC ◄─ T ◄─ SC` cannot occur after a removal operation. As
        a T can only ever have a single child.
        """
        nodes_to_remove = []
        n1, n2, n3 = node.parent.parent, node.parent, node

        if n3.is_sole_child:
            active_pruning_case = next(
                (
                    case
                    for case in self._pruning_cases
                    if all(
                        [
                            isinstance(n1, case.chain[0]),
                            isinstance(n2, case.chain[1]),
                            isinstance(n3, case.chain[2]),
                        ]
                    )
                ),
                None,
            )
            if active_pruning_case is not None:
                nodes_to_remove.extend(active_pruning_case.prune(n1, n2, n3))

        return nodes_to_remove

    def _prune_sc_sc_p(
        self, n1: SplitContainer, n2: SplitContainer, n3: Pane
    ) -> list[Node]:
        """n1 and n3 are linked together, n2 is discarded."""
        n2_position = n1.children.index(n2)
        n1.children.remove(n2)
        n3.parent = n1
        n1.children.insert(n2_position, n3)
        return [n2]

    def _prune_t_sc_sc(
        self, n1: Tab, n2: SplitContainer, n3: SplitContainer
    ) -> list[Node]:
        """n1 and n3 are linked together, n2 is discarded."""
        n2_position = n1.children.index(n2)
        n1.children.remove(n2)
        n3.parent = n1
        n1.children.insert(n2_position, n3)
        return [n2]

    def _prune_sc_sc_sc(
        self, n1: SplitContainer, n2: SplitContainer, n3: SplitContainer
    ) -> list[Node]:
        """n1 absorbs the children of n3. n2 and n3 are discarded."""
        n2_position = n1.children.index(n2)
        n1.children.remove(n2)
        for child in n3.children:
            child.parent = n1
            n1.children.insert(n2_position, child)
            n2_position += 1
        return [n3, n2]

    def _prune_sc_sc_tc(
        self, n1: SplitContainer, n2: SplitContainer, n3: TabContainer
    ) -> list[Node]:
        """n1 and n3 are linked together, n2 is discarded."""
        n2_position = n1.children.index(n2)
        n1.children.remove(n2)
        n3.parent = n1
        n1.children.insert(n2_position, n3)
        return [n2]

    def _prune_sc_tc_t(
        self, n1: SplitContainer, n2: TabContainer, n3: Tab
    ) -> list[Node]:
        """Depending on what is configured, this may lead to elimination of a subtab
        level - so n2 and n3 get discarded, linking n1 with n3's children.

        If the above pruning does happen, it leaves us with another possible opportunity
        to prune things if n1 and n3's child SC are of the same orientation.

        Elimination of a TC also leads to geometry adjustments due to the TC's tab bar
        also being eliminated.
        """
        removed_nodes = []
        hide_when = self.get_config("tab_bar.hide_when", level=n3.tab_level)
        if hide_when in ["always", "single_tab"]:
            n2_position = n1.children.index(n2)
            n1.children.remove(n2)
            sc = n3.children[0]

            # n3's T can only have a single SC child. The sc can now either match the n1
            # SC orientation or be different.
            if sc.axis == n1.axis:
                for child in sc.children:
                    child.parent = n1
                    n1.children.insert(n2_position, child)
                    n2_position += 1
                removed_nodes.append(sc)
            else:
                sc.parent = n1
                n1.children.insert(n2_position, sc)

            removed_nodes.extend([n3, n2])

            # Consume space left by tab bar after n2 is eliminated
            sc.transform(
                Axis.y,
                n2.principal_rect.y,
                sc.principal_rect.h + n2.tab_bar.box.principal_rect.h,
            )

        return removed_nodes

    def _prune_none_tc_t(self, n1: None, n2: TabContainer, n3: Tab) -> list[Node]:
        """As n1 is `None`, this is only applicable at the topmost tab level. There's no
        'pruning' per se, but when `tab_bar.hide_when` is configured to be `single_tab`,
        we need to hide the tab bar in this case.

        So only geometry adjustments are made to consume the space of the hidden tab
        bar.
        """
        hide_when = self.get_config("tab_bar.hide_when", level=n3.tab_level)
        if hide_when == "single_tab":
            bar_rect = n2.tab_bar.box.principal_rect
            bar_height = bar_rect.h
            bar_rect.h = 0
            n3.transform(Axis.y, bar_rect.y, n3.principal_rect.h + bar_height)
        return []

    def _find_super_node_to_resize(self, pane: Pane, axis: Axis) -> Node | None:
        """Finds the first node in the ancestor chain that is under a SC of the
        specified `axis`.
        """
        super_node = None
        n, p = pane, pane.parent
        while p is not None:
            if isinstance(p, SplitContainer):
                # A sole pane under a nested TC is a special case. During resize, it
                # behaves as if it were directly under said TC's container.
                n_is_sole_top_level_node = (
                    p.is_nearest_under_tab_container and p.has_single_child
                )
                if not n_is_sole_top_level_node and p.axis == axis:
                    super_node = n
                    break
            n, p = p, p.parent
        return super_node

    def _find_oriented_border_encompassing_super_node(
        self, pane: Pane, direction: Direction
    ) -> Node | None:
        """
        For the provided `pane's` border of the specified `direction`, finds the largest
        ancestor node that the pane's border is a subset of.

        The chosen super node is one that is of the correct 'orientation', ie. it is
        under a SC for which `sc.axis == direction.axis`.

        For the edge cases where there is no such oriented super node, `None` is
        returned. This happens when:
            - `pane` is a sole top level pane under the root TC
            - There are only top level panes under the root TC and the requested
              direction is in the inverse direction of those panes.
        """
        super_node = None
        n, p = pane, pane.parent
        while p is not None:
            if isinstance(p, SplitContainer) and p.axis == direction.axis:
                super_node = n
                edge_node = p.children[-1 if direction.axis_unit > 0 else 0]
                if n is not edge_node:
                    break
            n, p = p, p.parent
        return super_node

    def _find_panes_along_border(self, node: Node, direction: Direction) -> list[Pane]:
        if isinstance(node, Pane):
            return [node]

        if isinstance(node, TabContainer):
            sc = node.active_child.children[0]
            return self._find_panes_along_border(sc, direction)

        assert isinstance(node, SplitContainer)
        if node.axis == direction.axis:
            edge_node = node.children[0 if direction.axis_unit > 0 else -1]
            return self._find_panes_along_border(edge_node, direction)

        panes = []
        for inv_axis_child in node.children:
            panes.extend(self._find_panes_along_border(inv_axis_child, direction))
        return panes

    def _pick_mru_pane(self, panes: Iterable[Pane]) -> Pane:
        return sorted(panes, key=lambda p: p.recency, reverse=True)[0]

    def _next_tab(self, node: Node, n: int, *, wrap: bool = True) -> Pane | None:
        ancestor_tabs = node.get_ancestors(Tab, include_self=True)
        if not ancestor_tabs:
            raise ValueError("The provided node is not under a `TabContainer` node")

        next_tab = ancestor_tabs[0].sibling(n, wrap=wrap)
        if next_tab is None:
            return None

        return self._pick_mru_pane(self.iter_panes(start=next_tab))

    def _notify_subscribers(self, event: TreeEvent, nodes: list[Node]):
        for callback in self._event_subscribers[event].values():
            callback(nodes)


def tree_matches_repr(tree: Tree, test_repr: str) -> bool:
    tree_repr = textwrap.dedent(repr(tree)).strip()
    test_repr = textwrap.dedent(test_repr).strip()
    return tree_repr == test_repr


def repr_matches_repr(repr1: str, repr2: str) -> bool:
    repr1 = textwrap.dedent(repr1).strip()
    repr2 = textwrap.dedent(repr2).strip()
    return repr1 == repr2
