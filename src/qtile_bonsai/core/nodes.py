# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from __future__ import annotations

import abc
from typing import TypeVar

from qtile_bonsai.core.utils import Axis, AxisParam, UnitRect


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

    def get_first_ancestor(self, of_type: type[NodeType]) -> NodeType:
        node = self.parent
        while node is not None:
            if isinstance(node, of_type):
                return node
            node = node.parent
        raise ValueError(f"No node of type {of_type} in ancestor chain")

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


class NodeFactory:
    """Abstract factory class that enables consumers to extend the default `Node` family
    of classes to add any WM-specific constructs.

    These are the classes will be used internally by the `Tree` implementation.
    """

    TabContainer: type[TabContainer] = TabContainer
    Tab: type[Tab] = Tab
    SplitContainer: type[SplitContainer] = SplitContainer
    Pane: type[Pane] = Pane
