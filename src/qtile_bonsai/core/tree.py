# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from __future__ import annotations

import collections
import textwrap
import uuid
from typing import Callable, Iterable, Iterator

from strenum import StrEnum

from qtile_bonsai.core.geometry import Axis, AxisParam, Direction, DirectionParam, Rect
from qtile_bonsai.core.nodes import (
    Node,
    NodeFactory,
    Pane,
    SplitContainer,
    Tab,
    TabBar,
    TabContainer,
)
from qtile_bonsai.core.utils import validate_unit_range


class TreeEvent(StrEnum):
    node_added = "node_added"
    node_removed = "node_removed"


class InvalidTreeStructureError(Exception):
    pass


class Tree:
    TreeEventCallback = Callable[[list[Node]], None]
    _recency_seq = 0
    _prunable_chains = [
        (SplitContainer, SplitContainer, Pane),
        (Tab, SplitContainer, SplitContainer),
        (SplitContainer, SplitContainer, SplitContainer),
        (SplitContainer, SplitContainer, TabContainer),
    ]

    def __init__(
        self,
        width: int,
        height: int,
        *,
        node_factory: type[NodeFactory] | NodeFactory = NodeFactory,
    ):
        self._width: int = width
        self._height: int = height
        self._node_factory: type[NodeFactory] | NodeFactory = node_factory
        self._root: TabContainer | None = None
        self._event_subscribers: collections.defaultdict[
            TreeEvent, dict[str, Tree.TreeEventCallback]
        ] = collections.defaultdict(dict)

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def is_empty(self):
        return self._root is None

    def reset_dimensions(self, width: int, height: int):
        width_diff = width - self._width
        height_diff = height - self._height

        self._width = width
        self._height = height

        # Ensure the tree nodes get resized proportionally
        if self._root is not None:
            if width_diff > 0:
                self._root.grow(Axis.x, width_diff, 0)
            else:
                self._root.shrink(Axis.x, abs(width_diff), 0)
            if height_diff > 0:
                self._root.grow(Axis.y, height_diff, 0)
            else:
                self._root.shrink(Axis.y, abs(height_diff), 0)

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

    def split(self, pane: Pane, axis: AxisParam, ratio: float = 0.5) -> Pane:
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
            new_pane = self._node_factory.Pane(principal_rect=p2_rect)
            new_pane.parent = pane_container
            pane_container.children.insert(pane_index + 1, new_pane)
        else:
            pane_container.children.remove(pane)

            new_split_container = self._node_factory.SplitContainer()
            new_split_container.axis = axis
            new_split_container.parent = pane_container
            pane_container.children.insert(pane_index, new_split_container)
            added_nodes.append(new_split_container)

            pane.parent = new_split_container
            new_split_container.children.append(pane)

            new_pane = self._node_factory.Pane(principal_rect=p2_rect)
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

        assert super_node.operational_pair is not None
        operational_pair = super_node.operational_pair

        br_shrink = operational_pair[1] if amount > 0 else operational_pair[0]
        actual_amount = min(abs(amount), br_shrink.shrinkability(axis))

        if actual_amount > 0:
            b1, b2 = operational_pair
            b1_rect = b1.principal_rect
            b1_start = b1_rect.coord(axis)
            b1_end = b1_rect.coord2(axis)
            if amount > 0:
                b1.grow(axis, actual_amount, b1_start)
                b2.shrink(axis, actual_amount, b1_end + actual_amount)
            else:
                b1.shrink(axis, actual_amount, b1_start)
                b2.grow(axis, actual_amount, b1_end - actual_amount)

    def remove(self, pane: Pane) -> Pane | None:
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

        # Handle space redistribution if applicable
        if isinstance(container, SplitContainer):
            free_space = br_remove.principal_rect
            axis = container.axis
            start = min(free_space.coord(axis), br_sibling.principal_rect.coord(axis))
            br_sibling.grow(axis, free_space.dim(axis), start)

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

    def _add_very_first_tab(self) -> tuple[Pane, list[Node]]:
        """Add the first tab and its pane on an empty tree. A special case where the
        root is set and initial rects are set for use by all subsequent tabs and panes.
        """
        added_nodes = []

        # Max sized rect for top level tab bar
        tab_bar_rect = Rect(0, 0, self.width, TabBar.default_height)

        tab_container = self._node_factory.TabContainer()
        tab_container.tab_bar.box.principal_rect = tab_bar_rect
        added_nodes.append(tab_container)

        new_tab_title = f"{len(tab_container.children) + 1}"
        new_tab = self._node_factory.Tab(title=new_tab_title)
        new_tab.parent = tab_container
        tab_container.children.append(new_tab)
        tab_container.active_child = new_tab
        added_nodes.append(new_tab)

        new_split_container = self._node_factory.SplitContainer()
        new_split_container.parent = new_tab
        new_tab.children.append(new_split_container)
        added_nodes.append(new_split_container)

        # Max sized rect, allowing for top level tab bar
        new_pane_rect = Rect(
            0, tab_bar_rect.y2, self.width, self.height - tab_bar_rect.h
        )

        new_pane = self._node_factory.Pane(principal_rect=new_pane_rect)
        new_pane.parent = new_split_container
        new_split_container.children.append(new_pane)
        added_nodes.append(new_pane)

        self._root = tab_container

        return new_pane, added_nodes

    def _add_tab(self, tab_container: TabContainer) -> tuple[Pane, list[Node]]:
        added_nodes = []

        new_tab_title = f"{len(tab_container.children) + 1}"
        new_tab = self._node_factory.Tab(title=new_tab_title)
        new_tab.parent = tab_container
        tab_container.children.append(new_tab)
        added_nodes.append(new_tab)

        new_split_container = self._node_factory.SplitContainer()
        new_split_container.parent = new_tab
        new_tab.children.append(new_split_container)
        added_nodes.append(new_split_container)

        new_pane_rect = tab_container.get_inner_rect()

        new_pane = self._node_factory.Pane(principal_rect=new_pane_rect)
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

        new_tab_container = self._node_factory.TabContainer()
        new_tab_container.parent = at_split_container
        at_split_container.children.insert(at_pane_pos, new_tab_container)
        added_nodes.append(new_tab_container)

        # The new tab container's dimensions are derived from the space that was
        # occupied by `at_pane`
        new_tab_container.tab_bar.box.principal_rect = Rect(
            at_pane.principal_rect.x,
            at_pane.principal_rect.y,
            at_pane.principal_rect.w,
            TabBar.default_height,
        )

        tab1_title = f"{len(new_tab_container.children) + 1}"
        tab1 = self._node_factory.Tab(title=tab1_title)
        tab1.parent = new_tab_container
        new_tab_container.children.append(tab1)

        split_container1 = self._node_factory.SplitContainer()
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

        # Start adding the real new tab that was requested and mark it as the active
        # tab.
        tab2_title = f"{len(new_tab_container.children) + 1}"
        tab2 = self._node_factory.Tab(title=tab2_title)
        tab2.parent = new_tab_container
        new_tab_container.children.append(tab2)
        new_tab_container.active_child = tab2
        added_nodes.append(tab2)

        split_container2 = self._node_factory.SplitContainer()
        split_container2.parent = tab2
        tab2.children.append(split_container2)
        added_nodes.append(split_container2)

        # The new tab's pane will have the same dimensions as `at_pane` after it was
        # adjusted above.
        new_pane = self._node_factory.Pane(principal_rect=at_pane.principal_rect)
        new_pane.parent = split_container2
        split_container2.children.append(new_pane)
        added_nodes.append(new_pane)

        return new_pane, added_nodes

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
        top-down chain of `[n1, n2, n3]`. We look for opportunities to merge `n3` into
        `n1` and discard `n2`.

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

           SC ◄─┐
                │
                ├── TC ◄────── T
                │
         None ◄─┘

            T ◄─┐
                │
                ├── SC ◄────── TC
                │
          *SC ◄─┘


        Aside from the scenarios marked with *, the case of `TC ◄─ T ◄─ SC` cannot occur
        if n3 is to be left as a sole remnant child (the T can only have one child).
        """
        assert node.parent is not None
        nodes_to_remove = []

        n1, n2, n3 = node.parent.parent, node.parent, node
        if n3.is_sole_child and self._is_prunable_chain(n1, n2, n3):
            assert n1 is not None

            index = n1.children.index(n2)
            n1.children.remove(n2)

            if isinstance(n1, SplitContainer) and isinstance(n3, SplitContainer):
                # Here, even n3 gets discarded with n2. Only n1 remains which
                # absorbs the children of n3.
                for child in n3.children:
                    child.parent = n1
                    n1.children.insert(index, child)
                    index += 1
                nodes_to_remove.append(n3)
            else:
                n3.parent = n1
                n1.children.insert(index, n3)

            nodes_to_remove.append(n2)

        return nodes_to_remove

    def _is_prunable_chain(self, n1: Node, n2: Node, n3: Node) -> bool:
        for chain in self._prunable_chains:
            if all(
                [
                    isinstance(n1, chain[0]),
                    isinstance(n2, chain[1]),
                    isinstance(n3, chain[2]),
                ]
            ):
                return True
        return False

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
