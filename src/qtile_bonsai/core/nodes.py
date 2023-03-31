# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from __future__ import annotations

import abc
from typing import TypeVar

from qtile_bonsai.core.geometry import Axis, AxisParam, Box, Rect


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
    def principal_rect(self) -> Rect:
        raise NotImplementedError

    @abc.abstractmethod
    def shrinkability(self, axis: AxisParam) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def transform(self, axis: AxisParam, start: int, size: int):
        raise NotImplementedError

    @property
    def id(self) -> int:
        return self._id

    @property
    def children(self) -> list[Node]:
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
    def tab_level(self) -> int:
        """
        Returns the number of TabContainers under which this node exists.
        If this node is a TabContainer itself, it is also included in the count.
        Practical use benefits from this.
        """
        return len(self.get_ancestors(of_type=TabContainer, include_self=True))

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
    min_size: int = 50

    def __init__(
        self,
        *,
        content_rect: Rect | None = None,
        padding_rect: Rect | None = None,
        border_rect: Rect | None = None,
        margin_rect: Rect | None = None,
        principal_rect: Rect | None = None,
        margin: int = 0,
        border: int = 1,
        padding: int = 0,
    ):
        super().__init__()

        self.parent: SplitContainer
        self.box = Box(
            content_rect=content_rect,
            padding_rect=padding_rect,
            border_rect=border_rect,
            margin_rect=margin_rect,
            principal_rect=principal_rect,
            margin=margin,
            border=border,
            padding=padding,
        )
        self.recency: int = 0

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
    def principal_rect(self) -> Rect:
        return self.box.principal_rect

    @principal_rect.setter
    def principal_rect(self, value: Rect):
        self.box.principal_rect = value

    def shrinkability(self, axis: AxisParam) -> int:
        return self.principal_rect.dim(axis) - self.min_size

    def transform(self, axis: AxisParam, start: int, size: int):
        axis = Axis(axis)
        rect = self.box.principal_rect

        if size < self.min_size:
            raise ValueError("The new dimensions are not valid")

        setattr(rect, axis, start)
        setattr(rect, axis.dim, size)

    def __repr__(self) -> str:
        r = self.principal_rect
        return f"p:{self.id} | {{x: {r.x}, y: {r.y}, w: {r.w}, h: {r.h}}}"


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
    def principal_rect(self) -> Rect:
        rect = self.children[0].principal_rect
        for node in self.children[1:]:
            rect = rect.union(node.principal_rect)
        return rect

    def shrinkability(self, axis: AxisParam) -> int:
        shrinkability_summary = (child.shrinkability(axis) for child in self.children)
        if self.axis == axis:
            return sum(shrinkability_summary)
        return min(shrinkability_summary)

    def transform(self, axis: AxisParam, start: int, size: int):
        axis = Axis(axis)

        if self.axis == axis:
            # Resizing along `self.axis` will behave in a proportional manner.
            # When growing, each child node is grown in proportion to its size.
            # When shrinking, each child node is shrunk in proportion to its ability to
            # shrink to minimum possible size.
            branch_size = self.principal_rect.dim(axis)
            branch_shrinkability = self.shrinkability(axis)
            delta = size - branch_size
            s = start
            for child in self.children:
                child_size = child.principal_rect.dim(axis)

                if delta < 0:
                    # Handle shrinking in proportion to shrinkability of each child
                    child_shrinkability = child.shrinkability(axis)
                    allotment = round(
                        (child_shrinkability / branch_shrinkability) * delta
                    )
                else:
                    # Handle growing in proportion to each child's size
                    allotment = round((child_size / branch_size) * delta)

                new_child_size = child_size + allotment
                child.transform(axis, s, new_child_size)
                s += new_child_size
        else:
            # Resizing against `self.axis` will resize all contained nodes by the same
            # amount.
            for child in self.children:
                child.transform(axis, start, size)

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
    def principal_rect(self) -> Rect:
        return self.children[0].principal_rect

    def shrinkability(self, axis: AxisParam) -> int:
        return self.children[0].shrinkability(axis)

    def transform(self, axis: AxisParam, start: int, size: int):
        self.children[0].transform(axis, start, size)

    def __repr__(self) -> str:
        return f"t:{self.id}"


class TabContainer(Node):
    def __init__(self):
        super().__init__()

        self.parent: SplitContainer | None
        self.children: list[Tab]
        self.active_child: Tab | None = None
        self.tab_bar = TabBar(principal_rect=Rect(0, 0, 0, 0))

    @property
    def principal_rect(self) -> Rect:
        return self.get_inner_rect().union(self.tab_bar.box.principal_rect)

    def get_inner_rect(self) -> Rect:
        """Returns the space used by this TabContainer excluding its tab bar.

        All of the tabs under a tab container occupy the same total space, so we can
        just pick one.
        """
        return self.children[0].principal_rect

    def shrinkability(self, axis: AxisParam) -> int:
        # We are limited by what is contained in the nested tabs. The entire TC can only
        # shrink as much as the least shrinkable tab.
        return min(tab.shrinkability(axis) for tab in self.children)

    def transform(self, axis: AxisParam, start: int, size: int):
        bar_rect = self.tab_bar.box.principal_rect
        if axis == Axis.x:
            bar_rect.x = start
            bar_rect.w = size
        else:
            bar_rect.y = start

            # Adjust for tab bar before delegating to child nodes
            start += bar_rect.h
            size -= bar_rect.h

        for child in self.children:
            child.transform(axis, start, size)

    def __repr__(self) -> str:
        return f"tc:{self.id}"


class TabBar:
    def __init__(
        self,
        *,
        content_rect: Rect | None = None,
        padding_rect: Rect | None = None,
        border_rect: Rect | None = None,
        margin_rect: Rect | None = None,
        principal_rect: Rect | None = None,
        margin: int = 0,
        border: int = 1,
        padding: int = 0,
    ):
        self.box = Box(
            content_rect=content_rect,
            padding_rect=padding_rect,
            border_rect=border_rect,
            margin_rect=margin_rect,
            principal_rect=principal_rect,
            margin=margin,
            border=border,
            padding=padding,
        )
        self.bg_color = "#000000"
        self.fg_color = "#ff0000"
        self.active_tab_color = "#0000ff"

    @property
    def is_hidden(self):
        return self.box.principal_rect.h == 0
