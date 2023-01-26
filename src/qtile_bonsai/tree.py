# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from __future__ import annotations

import abc
import collections
import textwrap
import typing
import uuid
from typing import Callable, Iterable, Iterator, Literal, TypeVar

from libqtile.config import ScreenRect
from strenum import StrEnum

AxisLiteral = Literal["x", "y"]
DirectionLiteral = Literal["up", "down", "left", "right"]


class Axis(StrEnum):
    x = "x"
    y = "y"

    @property
    def inv(self) -> Axis:
        cls = self.__class__
        return cls.y if self == cls.x else cls.x

    @property
    def dim(self) -> str:
        cls = self.__class__
        return "w" if self == cls.x else "h"


class Direction(StrEnum):
    up = "up"
    down = "down"
    left = "left"
    right = "right"

    @property
    def inv(self) -> Direction:
        cls = self.__class__
        items = [cls.up, cls.right, cls.down, cls.left]
        return items[items.index(self) - 2]

    @property
    def axis(self) -> Axis:
        cls = self.__class__
        if self in [cls.left, cls.right]:
            return Axis.x
        return Axis.y

    @property
    def axis_unit(self) -> int:
        cls = self.__class__
        if self in [cls.left, cls.up]:
            return -1
        return 1


AxisParam = AxisLiteral | Axis
DirectionParam = DirectionLiteral | Direction


assert typing.get_args(AxisLiteral) == tuple(m.value for m in Axis)
assert typing.get_args(DirectionLiteral) == tuple(m.value for m in Direction)


class TreeEvent(StrEnum):
    node_added = "node_added"
    node_removed = "node_removed"


class UnitRect:
    def __init__(self, x: float, y: float, w: float, h: float):
        self._x = 0.0
        self._y = 0.0
        self._w = 0.0
        self._h = 0.0

        self.x = x
        self.y = y
        self.w = w
        self.h = h

    @property
    def x(self) -> float:
        return self._x

    @x.setter
    def x(self, value: float):
        validate_unit_range(value, "x")
        self._x = float(value)

    @property
    def y(self) -> float:
        return self._y

    @y.setter
    def y(self, value: float):
        validate_unit_range(value, "y")
        self._y = float(value)

    @property
    def w(self) -> float:
        return self._w

    @w.setter
    def w(self, value: float):
        validate_unit_range(value, "w")
        self._w = float(value)

    @property
    def h(self) -> float:
        return self._h

    @h.setter
    def h(self, value: float):
        validate_unit_range(value, "h")
        self._h = float(value)

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h

    def coord(self, axis: AxisParam):
        return getattr(self, axis)

    def coord2(self, axis: AxisParam):
        return getattr(self, f"{axis}2")

    def dim(self, axis: AxisParam):
        return getattr(self, Axis(axis).dim)

    def union(self, rect: UnitRect) -> UnitRect:
        x1 = min(self.x, rect.x)
        y1 = min(self.y, rect.y)
        x2 = max(self.x2, rect.x2)
        y2 = max(self.y2, rect.y2)

        return self.__class__(x1, y1, x2 - x1, y2 - y1)

    def to_screen_space(self, screen_rect: ScreenRect) -> ScreenRect:
        return ScreenRect(
            x=round(self.x * screen_rect.width),
            y=round(self.y * screen_rect.height),
            width=round(self.w * screen_rect.width),
            height=round(self.h * screen_rect.height),
        )

    @classmethod
    def from_rect(cls, rect: UnitRect) -> UnitRect:
        return cls(rect.x, rect.y, rect.w, rect.h)

    def __repr__(self) -> str:
        return f"{{x: {self.x}, y: {self.y}, w: {self.w}, h: {self.h}}}"

    def __eq__(self, other):
        if other is self:
            return True
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        raise NotImplementedError


class InvalidTreeStructureError(Exception):
    pass


class Node(metaclass=abc.ABCMeta):
    NodeType = TypeVar("NodeType", bound="Node")
    _id_seq = 0

    def __init__(self):
        # We specify `Node` explicitly to ensure continued sequence across instantiation
        # of any subclass instances.
        self._id = Node.next_id()

        self.parent: Node | None = None
        self._children: list[Node] = []

    @property
    @abc.abstractmethod
    def rect(self) -> UnitRect:
        raise NotImplementedError

    @abc.abstractmethod
    def shrinkability(self, axis: AxisParam) -> float:
        raise NotImplementedError

    @abc.abstractmethod
    def shrink(self, axis: AxisParam, amount: float, start_pos: float):
        raise NotImplementedError

    @abc.abstractmethod
    def grow(self, axis: AxisParam, amount: float, start_pos: float):
        raise NotImplementedError

    @property
    def id(self):
        return self._id

    @property
    def children(self):
        return self._children

    @property
    def has_single_child(self) -> bool:
        return len(self.children) == 1

    @property
    def is_sole_child(self) -> bool:
        if self.parent is None:
            raise AssertionError("This node has no parent")
        return self.parent.has_single_child

    @property
    def is_first_child(self) -> bool:
        if self.parent is None:
            raise AssertionError("This node has no parent")
        return self.parent.children[0] is self

    @property
    def is_last_child(self) -> bool:
        if self.parent is None:
            raise AssertionError("This node has no parent")
        return self.parent.children[-1] is self

    @property
    def operational_sibling(self) -> Node | None:
        parent = self.parent

        if parent is None or self.is_sole_child:
            return None

        index = parent.children.index(self)
        if index != len(parent.children) - 1:
            return parent.children[index + 1]

        # We are a rightmost node. Pick the left node instead in this case.
        return parent.children[-2]

    @property
    def operational_pair(self) -> tuple[Node, Node] | None:
        """A 2-tuple consisting of this node and a relevant sibling, in left-right
        tree order.

        The sibling is the collaborating node in various operations that modify the tree
        in some way.
        """
        parent = self.parent

        if parent is None:
            raise AssertionError("This node has no parent")

        if self.is_sole_child:
            return None

        index = parent.children.index(self)
        if index == len(parent.children) - 1:
            right = self
            left = parent.children[-2]
        else:
            left = self
            right = parent.children[index + 1]

        return (left, right)

    def sibling(self, n: int = 1, *, wrap: bool = False) -> Node | None:
        parent = self.parent

        if parent is None:
            raise AssertionError("This node has no parent")

        requested_index = parent.children.index(self) + n
        total = len(parent.children)
        if wrap:
            requested_index = requested_index % total
        if not wrap and not 0 <= requested_index < total:
            return None
        return parent.children[requested_index]

    def get_ancestors(
        self, of_type: type[NodeType] = None, *, include_self=False
    ) -> list[NodeType]:
        ancestors = [self] if include_self else []

        node = self.parent
        while node is not None:
            ancestors.append(node)
            node = node.parent

        if of_type is not None:
            ancestors = [node for node in ancestors if isinstance(node, of_type)]

        return ancestors

    def get_first_ancestor(self, of_type: type[NodeType]) -> NodeType | None:
        node = self.parent
        while node is not None:
            if isinstance(node, of_type):
                return node
            node = node.parent
        return None

    @classmethod
    def next_id(cls):
        cls._id_seq += 1
        return cls._id_seq

    @classmethod
    def reset_id_seq(cls):
        cls._id_seq = 0


class Pane(Node):
    min_size = 0.02

    def __init__(self, rect: UnitRect):
        super().__init__()

        self.parent: SplitContainer
        self.recency: int = 0
        self.rect = UnitRect.from_rect(rect)

    @property
    def is_nearest_under_tab_container(self):
        return isinstance(self.parent.parent.parent, TabContainer)

    @property
    def children(self):
        """A Pane cannot have children but will return an empty immutable tuple and
        raise an exception on trying to set it.
        This deviation of behaviour is to maintain the otherwise convenient interface on
        Node classes.
        """
        return ()

    @property
    def rect(self) -> UnitRect:
        return self._rect

    @rect.setter
    def rect(self, value: UnitRect):
        self._rect = value

    def shrinkability(self, axis: AxisParam) -> float:
        return self.rect.dim(axis) - self.min_size

    def shrink(self, axis: AxisParam, amount: float, start_pos: float):
        axis = Axis(axis)
        setattr(self.rect, axis, start_pos)
        new_dimension = max(self.rect.dim(axis) - amount, self.min_size)
        setattr(self.rect, axis.dim, new_dimension)

    def grow(self, axis: AxisParam, amount: float, start_pos: float):
        axis = Axis(axis)
        setattr(self.rect, axis, start_pos)
        new_dimension = min(self.rect.dim(axis) + amount, 1)
        setattr(self.rect, axis.dim, new_dimension)

    def __repr__(self) -> str:
        r = self.rect
        return f"p:{self.id} | {{x: {r.x:.4}, y: {r.y:.4}, w: {r.w:.4}, h: {r.h:.4}}}"


class SplitContainer(Node):
    def __init__(self):
        super().__init__()

        self.parent: Tab | SplitContainer
        self.children: list[SplitContainer | Pane | TabContainer]
        self.axis: Axis = Axis.x

    @property
    def is_nearest_under_tab_container(self):
        return isinstance(self.parent.parent, TabContainer)

    @property
    def rect(self) -> UnitRect:
        rect = self.children[0].rect
        for node in self.children[1:]:
            rect = rect.union(node.rect)
        return rect

    def shrinkability(self, axis: AxisParam) -> float:
        shrinkability_summary = (child.shrinkability(axis) for child in self.children)
        if self.axis == axis:
            return sum(shrinkability_summary)
        return min(shrinkability_summary)

    def shrink(self, axis: AxisParam, amount: float, start_pos: float):
        branch_shrinkability = self.shrinkability(axis)
        actual_amount = min(amount, branch_shrinkability)
        if self.axis == axis:
            # Resizing along `self.axis` will shrink each contained node in proportion
            # to its ability to shrink.
            s = start_pos
            for child in self.children:
                child_shrinkability = child.shrinkability(axis)
                allotment = (child_shrinkability / branch_shrinkability) * actual_amount
                child.shrink(axis, allotment, s)
                s += child.rect.dim(axis)
        else:
            # Resizing against `self.axis` will shrink all contained nodes by the same
            # amount.
            for child in self.children:
                child.shrink(axis, actual_amount, start_pos)

    def grow(self, axis: AxisParam, amount: float, start_pos: float):
        if self.axis == axis:
            # Resizing along `self.axis` will grow each contained node in proportion
            # to its size.
            branch_size = self.rect.dim(axis)
            s = start_pos
            for child in self.children:
                child_size = child.rect.dim(axis)
                allotment = (child_size / branch_size) * amount
                child.grow(axis, allotment, s)
                s += child_size + allotment
        else:
            # Resizing against `self.axis` will grow all contained nodes by the same
            # amount.
            for child in self.children:
                child.grow(axis, amount, start_pos)

    def __repr__(self) -> str:
        return f"sc.{self.axis}:{self.id}"


class Tab(Node):
    """A `Tab` is an intermediate node under a `TabContainer` that holds some metadata
    about the entire tab. A `Tab` instance has only a single child - a `SplitContainer`.
    """

    def __init__(self, title):
        super().__init__()

        self.parent: TabContainer
        self.children: list[SplitContainer]
        self.title: str = title
        self.last_focused_pane: Pane | None = None

    @property
    def rect(self) -> UnitRect:
        return self.children[0].rect

    def shrinkability(self, axis: AxisParam) -> float:
        return self.children[0].shrinkability(axis)

    def shrink(self, axis: AxisParam, amount: float, start_pos: float):
        self.children[0].shrink(axis, amount, start_pos)

    def grow(self, axis: AxisParam, amount: float, start_pos: float):
        self.children[0].grow(axis, amount, start_pos)

    def __repr__(self) -> str:
        return f"t:{self.id}"


class TabContainer(Node):
    def __init__(self):
        super().__init__()

        self.parent: SplitContainer | None
        self.children: list[Tab]
        self.active_child: Tab | None = None
        self.tab_bar = TabBar()

    @property
    def rect(self) -> UnitRect:
        return self.get_inner_rect().union(self.tab_bar.rect)

    def get_inner_rect(self) -> UnitRect:
        """Returns the space used by this TabContainer excluding its tab bar.

        All of the tabs under a tab container occupy the same total space, so we can
        just pick one.
        """
        return self.children[0].rect

    def shrinkability(self, axis: AxisParam) -> float:
        # We are limited by what is contained in the nested tabs. The entire TC can only
        # shrink as much as the least shrinkable tab.
        return min(tab.shrinkability(axis) for tab in self.children)

    def shrink(self, axis: AxisParam, amount: float, start_pos: float):
        actual_amount = min(amount, self.shrinkability(axis))

        if axis == "x":
            self.tab_bar.rect.x = start_pos
            self.tab_bar.rect.w -= actual_amount
        else:
            self.tab_bar.rect.y = start_pos
            start_pos += self.tab_bar.rect.h

        for child in self.children:
            child.shrink(axis, actual_amount, start_pos)

    def grow(self, axis: AxisParam, amount: float, start_pos: float):
        if axis == "x":
            self.tab_bar.rect.x = start_pos
            self.tab_bar.rect.w += amount
        else:
            self.tab_bar.rect.y = start_pos
            start_pos += self.tab_bar.rect.h

        for child in self.children:
            child.grow(axis, amount, start_pos)

    def __repr__(self) -> str:
        return f"tc:{self.id}"


class TabBar:
    default_height = 0.02

    def __init__(self):
        self.rect = UnitRect(0, 0, 1, self.default_height)
        self.bg_color = "#000000"
        self.fg_color = "#ff0000"
        self.active_tab_color = "#0000ff"


class Tree:
    TreeEventCallback = Callable[[list[Node]], None]
    _recency_seq = 0

    def __init__(self):
        self._root: TabContainer | None = None
        self._event_subscribers: collections.defaultdict[
            TreeEvent, dict[str, Tree.TreeEventCallback]
        ] = collections.defaultdict(dict)

    @property
    def is_empty(self):
        return self._root is None

    def add_tab(
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

        r = pane.rect
        if axis == "x":
            p1_size = r.w * ratio
            p1_rect = UnitRect(r.x, r.y, p1_size, r.h)
            p2_rect = UnitRect(r.x + p1_size, r.y, r.w - p1_size, r.h)
        else:
            p1_size = r.h * ratio
            p1_rect = UnitRect(r.x, r.y, r.w, p1_size)
            p2_rect = UnitRect(r.x, r.y + p1_size, r.w, r.h - p1_size)

        pane.rect = p1_rect

        # During the flow below, we try to ensure `new_pane` is created after any other
        # new nodes to maintain ID sequence.
        if pane_container.axis == axis:
            new_pane = Pane(p2_rect)
            new_pane.parent = pane_container
            pane_container.children.insert(pane_index + 1, new_pane)
        else:
            pane_container.children.remove(pane)

            new_split_container = SplitContainer()
            new_split_container.axis = axis
            new_split_container.parent = pane_container
            pane_container.children.insert(pane_index, new_split_container)
            added_nodes.append(new_split_container)

            pane.parent = new_split_container
            new_split_container.children.append(pane)

            new_pane = Pane(p2_rect)
            new_pane.parent = new_split_container
            new_split_container.children.append(new_pane)

        added_nodes.append(new_pane)

        self._notify_subscribers(TreeEvent.node_added, added_nodes)

        return new_pane

    def resize(self, pane: Pane, axis: AxisParam, amount: float):
        if not -1 <= amount <= 1:
            raise ValueError("`amount` must be between -1 and 1")

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
            b1_rect = b1.rect
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
            free_space = br_remove.rect
            axis = container.axis
            start = min(free_space.coord(axis), br_sibling.rect.coord(axis))
            br_sibling.grow(axis, free_space.dim(axis), start)

        removed_nodes.extend(self._do_post_removal_pruning(br_sibling))

        self._notify_subscribers(TreeEvent.node_removed, removed_nodes)

        next_focus_pane = self._pick_mru_pane(self.iter_panes(start=br_sibling))

        return next_focus_pane

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
                node.last_focused_pane = pane
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
            coord1_ok = candidate.rect.coord(inv_axis) < pane.rect.coord2(inv_axis)
            coord2_ok = candidate.rect.coord2(inv_axis) > pane.rect.coord(inv_axis)
            if coord1_ok and coord2_ok:
                adjacent.append(candidate)

        return adjacent

    def iter_walk(self, start: Node | None = None):
        if self.is_empty:
            return

        def walk(node):
            yield node
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
        tab_bar_rect = UnitRect(0, 0, 1, TabBar.default_height)

        tab_container = TabContainer()
        tab_container.tab_bar.rect = tab_bar_rect
        added_nodes.append(tab_container)

        new_tab_title = f"{len(tab_container.children) + 1}"
        new_tab = Tab(title=new_tab_title)
        new_tab.parent = tab_container
        tab_container.children.append(new_tab)
        tab_container.active_child = new_tab
        added_nodes.append(new_tab)

        new_split_container = SplitContainer()
        new_split_container.parent = new_tab
        new_tab.children.append(new_split_container)
        added_nodes.append(new_split_container)

        # Max sized rect, allowing for top level tab bar
        new_pane_rect = UnitRect(tab_bar_rect.x, tab_bar_rect.y2, 1, 1 - tab_bar_rect.h)

        new_pane = Pane(new_pane_rect)
        new_pane.parent = new_split_container
        new_split_container.children.append(new_pane)
        added_nodes.append(new_pane)

        self._root = tab_container

        return new_pane, added_nodes

    def _add_tab(self, tab_container: TabContainer) -> tuple[Pane, list[Node]]:
        added_nodes = []

        new_tab_title = f"{len(tab_container.children) + 1}"
        new_tab = Tab(title=new_tab_title)
        new_tab.parent = tab_container
        tab_container.children.append(new_tab)
        added_nodes.append(new_tab)

        new_split_container = SplitContainer()
        new_split_container.parent = new_tab
        new_tab.children.append(new_split_container)
        added_nodes.append(new_split_container)

        new_pane_rect = tab_container.get_inner_rect()

        new_pane = Pane(new_pane_rect)
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

        new_tab_container = TabContainer()
        new_tab_container.parent = at_split_container
        at_split_container.children.insert(at_pane_pos, new_tab_container)
        added_nodes.append(new_tab_container)

        # The new tab container's dimensions are derived from the space that was
        # occupied by `at_pane`
        new_tab_container.tab_bar.rect = UnitRect(
            at_pane.rect.x,
            at_pane.rect.y,
            at_pane.rect.w,
            TabBar.default_height,
        )

        tab1_title = f"{len(new_tab_container.children) + 1}"
        tab1 = Tab(title=tab1_title)
        tab1.parent = new_tab_container
        new_tab_container.children.append(tab1)

        split_container1 = SplitContainer()
        split_container1.parent = tab1
        tab1.children.append(split_container1)

        # Attach `at_pane` under the first tab of our new subtree.
        at_pane.parent = split_container1
        split_container1.children.append(at_pane)

        # Adjust `at_pane's` dimensions to account for the new tab bar
        at_pane.rect.y = new_tab_container.tab_bar.rect.y2
        at_pane.rect.h -= new_tab_container.tab_bar.rect.h

        # Start adding the real new tab that was requested and mark it as the active
        # tab.
        tab2_title = f"{len(new_tab_container.children) + 1}"
        tab2 = Tab(title=tab2_title)
        tab2.parent = new_tab_container
        new_tab_container.children.append(tab2)
        new_tab_container.active_child = tab2
        added_nodes.append(tab2)

        split_container2 = SplitContainer()
        split_container2.parent = tab2
        tab2.children.append(split_container2)
        added_nodes.append(split_container2)

        # The new tab's pane will have the same dimensions as `at_pane` after it was
        # adjusted above.
        new_pane = Pane(at_pane.rect)
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

        All the `[n1, n2, n3]` possibilities are listed below. The chains that are
        prunable are marked with *.

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
        if n3.is_sole_child:
            prunable_chains = [
                (SplitContainer, SplitContainer, Pane),
                (Tab, SplitContainer, SplitContainer),
                (SplitContainer, SplitContainer, SplitContainer),
                (SplitContainer, SplitContainer, TabContainer),
            ]
            if (type(n1), type(n2), type(n3)) in prunable_chains:
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
        elif isinstance(node, TabContainer):
            sc = node.active_child.children[0]
            return self._find_panes_along_border(sc, direction)
        else:
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


def validate_unit_range(value: float, field_name: str):
    if not (0 <= value <= 1):
        raise ValueError(f"Value of `{field_name}` must be between 0 and 1 inclusive.")


def tree_matches_repr(tree: Tree, test_repr: str) -> bool:
    tree_repr = textwrap.dedent(repr(tree)).strip()
    test_repr = textwrap.dedent(test_repr).strip()
    return tree_repr == test_repr
