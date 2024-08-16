# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from __future__ import annotations

import abc
from typing import TypeVar

from qtile_bonsai.core.geometry import (
    Axis,
    AxisParam,
    Box,
    Direction1D,
    PerimieterParams,
    Rect,
)


class Node(metaclass=abc.ABCMeta):
    NodeType = TypeVar("NodeType", bound="Node")
    _id_seq = 0

    def __init__(self):
        # We specify `Node` explicitly to ensure continued sequence across instantiation
        # of any subclass instances.
        self.id: int = Node.next_id()

        self.parent: Node | None = None
        self.children: list[Node] = []

    @property
    @abc.abstractmethod
    def principal_rect(self) -> Rect:
        pass

    @property
    @abc.abstractmethod
    def is_nearest_under_tc(self) -> bool:
        pass

    @abc.abstractmethod
    def shrinkability(self, axis: AxisParam) -> int:
        pass

    @abc.abstractmethod
    def transform(self, axis: AxisParam, start: int, size: int):
        pass

    @abc.abstractmethod
    def get_participants_for_split_op(
        self, axis: Axis, position: Direction1D
    ) -> tuple[SplitContainer | None, Node, int]:
        """Return participants that would be invovled in a split operation on this node.

        Returns:
            A 3-tuple:
                1. The SplitContainer under which the new split's contents should be
                    added or `None` if no suitable SC of the desired orientation exists.
                    In that case, the caller would create a new SC.
                2. The node that would actually be split (and possibly inserted under a
                    new SC). The node to use for geometry adjustment calculations.
                    This is usually `self`.
                3. The index where the new split content would be added. Also valid when
                    tuple.0 is None - in which case it is the index under the new SC
                    that would later be created.
        """
        pass

    @abc.abstractmethod
    def as_dict(self) -> dict:
        """Provide a plain dict prepresentation of this node. Handy for things like
        serialization.
        """
        return {
            "type": self.abbrv(),
            "id": self.id,
            "children": [child.as_dict() for child in self.children],
        }

    @abc.abstractmethod
    def __str__(self) -> str:
        pass

    @classmethod
    @abc.abstractmethod
    def abbrv(cls) -> str:
        pass

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
        self, of_type: type[NodeType] = None, *, include_self: bool = False
    ) -> list[NodeType]:
        ancestors = [self] if include_self else []

        node = self.parent
        while node is not None:
            ancestors.append(node)
            node = node.parent

        if of_type is not None:
            ancestors = [node for node in ancestors if isinstance(node, of_type)]

        return ancestors

    def get_first_ancestor(
        self, of_type: type[NodeType] | tuple[type[NodeType], ...]
    ) -> NodeType:
        node = self.parent
        while node is not None:
            if isinstance(node, of_type):
                return node
            node = node.parent
        raise ValueError(f"No node of type {of_type} in ancestor chain")

    def get_self_or_first_ancestor(self, of_type: type[NodeType]) -> NodeType:
        if isinstance(self, of_type):
            return self
        return self.get_first_ancestor(of_type)

    def __repr__(self):
        return f"{self.abbrv()}:{self.id}"

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
        principal_rect: Rect,
        *,
        margin: PerimieterParams = 0,
        border: PerimieterParams = 1,
        padding: PerimieterParams = 0,
    ):
        super().__init__()

        self.parent: SplitContainer
        self.box = Box(
            principal_rect=principal_rect,
            margin=margin,
            border=border,
            padding=padding,
        )
        self.recency: int = 0

    @property
    def is_nearest_under_tc(self) -> bool:
        return isinstance(self.parent.parent.parent, TabContainer)

    @property
    def principal_rect(self) -> Rect:
        return self.box.principal_rect

    @principal_rect.setter
    def principal_rect(self, value: Rect):
        self.box.principal_rect = value

    def shrinkability(self, axis: AxisParam) -> int:
        return self.principal_rect.size(axis) - self.min_size

    def transform(self, axis: AxisParam, start: int, size: int):
        axis = Axis(axis)
        rect = self.box.principal_rect

        if size < self.min_size:
            raise ValueError("The new dimensions are not valid")

        setattr(rect, axis, start)
        setattr(rect, axis.dim, size)

    def get_participants_for_split_op(
        self, axis: Axis, position: Direction1D
    ) -> tuple[SplitContainer | None, Node, int]:
        parent = self.parent
        if parent.axis != axis:
            return (None, self, 1 if position == Direction1D.next else 0)

        index = parent.children.index(self)
        return (parent, self, index + 1 if position == Direction1D.next else index)

    def as_dict(self) -> dict:
        return {
            **super().as_dict(),
            "box": self.box.as_dict(),
        }

    def __str__(self) -> str:
        r = self.principal_rect
        return f"{self.abbrv()}:{self.id} | {{x: {r.x}, y: {r.y}, w: {r.w}, h: {r.h}}}"

    @classmethod
    def abbrv(cls) -> str:
        return "p"


class SplitContainer(Node):
    def __init__(self):
        super().__init__()

        self.parent: Tab | SplitContainer
        self.children: list[SplitContainer | Pane | TabContainer]
        self.axis: Axis = Axis.x

    @property
    def is_nearest_under_tc(self) -> bool:
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
            branch_size = self.principal_rect.size(axis)
            branch_shrinkability = self.shrinkability(axis)
            delta = size - branch_size
            s = start
            for child in self.children:
                child_size = child.principal_rect.size(axis)

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

    def get_participants_for_split_op(
        self, axis: Axis, position: Direction1D
    ) -> tuple[SplitContainer | None, Node, int]:
        parent = self.parent

        if self.axis == axis:
            return (
                self,
                self,
                len(self.children) if position == Direction1D.next else 0,
            )
        if self.is_nearest_under_tc and self.is_sole_child:
            return (None, self, 1 if position == Direction1D.next else 0)

        assert isinstance(parent, SplitContainer)

        index = parent.children.index(self)
        return (parent, self, index + 1 if position == Direction1D.next else index)

    def as_dict(self) -> dict:
        return {
            **super().as_dict(),
            "axis": Axis(self.axis).value,
        }

    def __str__(self) -> str:
        return f"{self.abbrv()}.{self.axis}:{self.id}"

    @classmethod
    def abbrv(cls) -> str:
        return "sc"


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
        return Rect.from_rect(self.children[0].principal_rect)

    @property
    def is_nearest_under_tc(self) -> bool:
        return True

    def shrinkability(self, axis: AxisParam) -> int:
        return self.children[0].shrinkability(axis)

    def transform(self, axis: AxisParam, start: int, size: int):
        self.children[0].transform(axis, start, size)

    def get_participants_for_split_op(
        self, axis: Axis, position: Direction1D
    ) -> tuple[SplitContainer | None, Node, int]:
        return self.parent.get_participants_for_split_op(axis, position)

    def as_dict(self) -> dict:
        return {
            **super().as_dict(),
            "title": self.title,
        }

    def __str__(self) -> str:
        return f"{self.abbrv()}:{self.id}"

    @classmethod
    def abbrv(cls) -> str:
        return "t"


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

    @property
    def is_nearest_under_tc(self) -> bool:
        if self.parent is not None:
            return self.parent.is_nearest_under_tc
        raise ValueError("This is either the root TC or an orphan TC")

    def get_inner_rect(self) -> Rect:
        """Returns the space used by this TabContainer excluding its tab bar.

        All of the tabs under a tab container occupy the same total space, so we can
        just pick one.
        """
        return Rect.from_rect(self.children[0].principal_rect)

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

    def get_participants_for_split_op(
        self, axis: Axis, position: Direction1D
    ) -> tuple[SplitContainer | None, Node, int]:
        parent = self.parent
        if parent is None:
            raise ValueError("Invalid node for split operation")

        if parent.axis != axis:
            return (None, self, 1 if position == Direction1D.next else 0)

        index = parent.children.index(self)
        return (parent, self, index + 1 if position == Direction1D.next else index)

    def expand_tab_bar(self, bar_height: int):
        rect = self.principal_rect
        self.tab_bar.box.principal_rect.h = bar_height
        for tab in self.children:
            tab.transform(Axis.y, rect.y + bar_height, rect.h - bar_height)

    def collapse_tab_bar(self):
        rect = self.principal_rect
        self.tab_bar.box.principal_rect.h = 0
        for tab in self.children:
            tab.transform(Axis.y, rect.y, rect.h)

    def as_dict(self) -> dict:
        return {
            **super().as_dict(),
            "active_child": self.active_child.id,
            "tab_bar": self.tab_bar.as_dict(),
        }

    def __str__(self) -> str:
        return f"{self.abbrv()}:{self.id}"

    @classmethod
    def abbrv(cls) -> str:
        return "tc"


class TabBar:
    def __init__(
        self,
        principal_rect: Rect,
        *,
        margin: PerimieterParams = 0,
        border: PerimieterParams = 1,
        padding: PerimieterParams = 0,
    ):
        self.box = Box(
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

    def as_dict(self) -> dict:
        return {"box": self.box.as_dict()}
