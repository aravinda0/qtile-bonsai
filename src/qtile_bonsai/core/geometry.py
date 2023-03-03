# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from __future__ import annotations

import typing
from typing import Literal

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


class Rect:
    def __init__(self, x: int, y: int, w: int, h: int):
        self._x = 0
        self._y = 0
        self._w = 0
        self._h = 0

        self.x = x
        self.y = y
        self.w = w
        self.h = h

    @property
    def x(self) -> int:
        return self._x

    @x.setter
    def x(self, value: int):
        self._x = value

    @property
    def y(self) -> int:
        return self._y

    @y.setter
    def y(self, value: int):
        self._y = value

    @property
    def w(self) -> int:
        return self._w

    @w.setter
    def w(self, value: int):
        self._w = value

    @property
    def h(self) -> int:
        return self._h

    @h.setter
    def h(self, value: int):
        self._h = value

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    def coord(self, axis: AxisParam):
        return getattr(self, axis)

    def coord2(self, axis: AxisParam):
        return getattr(self, f"{axis}2")

    def dim(self, axis: AxisParam):
        return getattr(self, Axis(axis).dim)

    def union(self, rect: Rect) -> Rect:
        x1 = min(self.x, rect.x)
        y1 = min(self.y, rect.y)
        x2 = max(self.x2, rect.x2)
        y2 = max(self.y2, rect.y2)

        return self.__class__(x1, y1, x2 - x1, y2 - y1)

    def split(self, axis: AxisParam, ratio: float = 0.5) -> tuple[Rect, Rect]:
        """Returns two new Rect instances that have dimensions according to the
        requested split.

        NOTE: Currently Rect(0, 0, 100, 100) gets x-split into Rect(0, 0, 50, 100),
        Rect(50, 0, 50, 100). ie. in pixel terms, depending on the rendering engine, it
        could be that the end border of rect1 occupies the same pixels as the start
        border of rect2.

        TODO: Review and see if we want to change this to do a +1 on rect2 and adjust
        its dimension accordingly.
        """
        axis = Axis(axis)
        cls = self.__class__

        if axis == Axis.x:
            w = round(self.w * ratio)
            r1 = cls(self.x, self.y, w, self.h)
            r2 = cls(self.x + w, self.y, self.w - w, self.h)
        else:
            h = round(self.h * ratio)
            r1 = cls(self.x, self.y, self.w, h)
            r2 = cls(self.x, self.y + h, self.w, self.h - h)

        return (r1, r2)

    @classmethod
    def from_rect(cls, rect: Rect) -> Rect:
        return cls(rect.x, rect.y, rect.w, rect.h)

    def __repr__(self) -> str:
        return f"{{x: {self.x}, y: {self.y}, w: {self.w}, h: {self.h}}}"

    def __eq__(self, other):
        if other is self:
            return True
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        raise NotImplementedError


class Box:
    """Provides rect-geometry akin to the CSS box model.

    The concentric rects, innermost to outermost are:
        1. margin_rect/principal_rect
        2. border_rect
        3. padding_rect
        4. content_rect

    We can set any of the rects and the internals will be sync'd according to the
    margin/border/padding values, so that accessing any rect property subsequently will
    work correctly.

    The `principal_rect` is a synonym for the outermost rect and represents the maximum
    space occupied by the box. In the current model, it is the same as `margin_rect`.

    Comparing to CSS, where the box semantics default to 'content-box', our Box class
    defaults to what could be defined as 'margin-box' or 'principal-box'.

    This 'principal-box' model is more suitable for use in tiling window managers, where
    we start out with a full screen-sized rect, and keep dividing that rect into smaller
    ones. So even if we keep tweaking margins/borders/padding, the principal_rect
    relationships between different windows remains constant and simplifies
    calculations.

    NOTE: At the moment, we must be wary of doing something like
    `box.content_rect.x = 100` - which cant't trigger the sync logic.
    """

    def __init__(
        self,
        *,
        principal_rect: Rect | None = None,
        margin_rect: Rect | None = None,
        border_rect: Rect | None = None,
        padding_rect: Rect | None = None,
        content_rect: Rect | None = None,
        margin: int = 0,
        border: int = 1,
        padding: int = 0,
    ):
        self.margin: int = margin
        self.border: int = border
        self.padding: int = padding
        self._init_rect(
            principal_rect,
            margin_rect,
            border_rect,
            padding_rect,
            content_rect,
        )

    @property
    def principal_rect(self) -> Rect:
        return self.margin_rect

    @principal_rect.setter
    def principal_rect(self, value: Rect):
        self.margin_rect = value

    @property
    def margin_rect(self) -> Rect:
        return self._margin_rect

    @margin_rect.setter
    def margin_rect(self, value: Rect):
        self._margin_rect = Rect.from_rect(value)

    @property
    def border_rect(self) -> Rect:
        return self._get_inner_rect(self.margin)

    @border_rect.setter
    def border_rect(self, value: Rect):
        excess_per_side = self.margin
        self._set_principal_rect(value, excess_per_side)

    @property
    def padding_rect(self) -> Rect:
        return self._get_inner_rect(self.margin + self.border)

    @padding_rect.setter
    def padding_rect(self, value: Rect):
        excess_per_side = self.margin + self.padding
        self._set_principal_rect(value, excess_per_side)

    @property
    def content_rect(self) -> Rect:
        return self._get_inner_rect(self.margin + self.border + self.padding)

    @content_rect.setter
    def content_rect(self, value: Rect):
        excess_per_side = self.margin + self.border + self.padding
        self._set_principal_rect(value, excess_per_side)

    def __repr__(self):
        r = self.principal_rect
        m, b, p = self.margin, self.border, self.padding
        return f"{{x: {r.x}, y: {r.y}, w: {r.w}, h: {r.h}, m: {m}, b: {b}, p: {p}}}"

    def _init_rect(
        self,
        principal_rect: Rect | None = None,
        margin_rect: Rect | None = None,
        border_rect: Rect | None = None,
        padding_rect: Rect | None = None,
        content_rect: Rect | None = None,
    ):
        rect_args = [
            principal_rect,
            margin_rect,
            border_rect,
            padding_rect,
            content_rect,
        ]
        non_null_rect_args = len([rect for rect in rect_args if rect is not None])
        if non_null_rect_args != 1:
            raise ValueError(
                "A single rect out of [content_rect, padding_rect, border_rect, "
                f"margin_rect, principal_rect] must be provided. {non_null_rect_args} "
                "have been provided."
            )

        if principal_rect is not None:
            self.principal_rect = principal_rect
        elif margin_rect is not None:
            self.margin_rect = margin_rect
        elif border_rect is not None:
            self.border_rect = border_rect
        elif padding_rect is not None:
            self.padding_rect = padding_rect
        elif content_rect is not None:
            self.content_rect = content_rect

    def _get_inner_rect(self, excess_per_side: int) -> Rect:
        x = self.principal_rect.x + excess_per_side
        y = self.principal_rect.y + excess_per_side
        w = self.principal_rect.w - (2 * excess_per_side)
        h = self.principal_rect.h - (2 * excess_per_side)
        return Rect(x, y, w, h)

    def _set_principal_rect(self, inner_rect: Rect, excess_per_side: int):
        x = inner_rect.x - excess_per_side
        y = inner_rect.y - excess_per_side
        w = inner_rect.w + (2 * excess_per_side)
        h = inner_rect.h + (2 * excess_per_side)
        self.margin_rect = Rect(x, y, w, h)
