# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from __future__ import annotations

import typing
from collections.abc import Sequence
from typing import Literal

from strenum import StrEnum

from qtile_bonsai.core.utils import all_or_none


AxisLiteral = Literal["x", "y"]
DirectionLiteral = Literal["up", "down", "left", "right"]
Direction1DLiteral = Literal["previous", "next"]


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


class Direction1D(StrEnum):
    previous = "previous"
    next = "next"

    @property
    def axis_unit(self) -> int:
        cls = self.__class__
        if self == cls.previous:
            return -1
        return 1


AxisParam = AxisLiteral | Axis
DirectionParam = DirectionLiteral | Direction
Direction1DParam = Direction1DLiteral | Direction1D


assert typing.get_args(AxisLiteral) == tuple(m.value for m in Axis)
assert typing.get_args(DirectionLiteral) == tuple(m.value for m in Direction)
assert typing.get_args(Direction1DLiteral) == tuple(m.value for m in Direction1D)


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

    def size(self, axis: AxisParam):
        return getattr(self, Axis(axis).dim)

    def union(self, rect: Rect) -> Rect:
        x1 = min(self.x, rect.x)
        y1 = min(self.y, rect.y)
        x2 = max(self.x2, rect.x2)
        y2 = max(self.y2, rect.y2)

        return self.__class__(x1, y1, x2 - x1, y2 - y1)

    def has_coord(self, x: int, y: int) -> bool:
        if x >= self.x and x < self.x2 and y >= self.y and y < self.y2:
            return True
        return False

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

    def as_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}

    @classmethod
    def from_rect(cls, rect: Rect) -> Rect:
        return cls(rect.x, rect.y, rect.w, rect.h)

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return repr(self.as_dict())

    def __eq__(self, other):
        if other is self:
            return True
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        raise NotImplementedError


class Perimeter:
    """Represents a perimeter around a rect - eg. margin, border, padding.

    Supports the 'thickness' or 'size' on each side of the rect - top, right, bottom,
    left.
    """

    def __init__(
        self,
        top_or_all: int | list[int],
        right: int | None = None,
        bottom: int | None = None,
        left: int | None = None,
    ):
        if isinstance(top_or_all, Sequence):
            [self.top, self.right, self.bottom, self.left] = top_or_all
        else:
            right, bottom, left = all_or_none(right, bottom, left)
            if [right, bottom, left] == [None] * 3:
                right, bottom, left = [top_or_all] * 3

            self.top: int = top_or_all
            self.right: int = right
            self.bottom: int = bottom
            self.left: int = left

    def as_list(self):
        """Return perimeter values as a 4-item list in CSS-esque ordering:
        [top, right, bottom, left].
        """
        return [self.top, self.right, self.bottom, self.left]

    def as_dict(self):
        return {
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
            "left": self.left,
        }


PerimieterParams = int | list[int] | Perimeter


class Box:
    """Provides rect-geometry akin to the CSS box model.

    The concentric rects, outermost to innermost are:
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
    """

    _principal_rect: Rect
    _margin: Perimeter
    _border: Perimeter
    _padding: Perimeter

    def __init__(
        self,
        principal_rect: Rect,
        *,
        margin: PerimieterParams = 0,
        border: PerimieterParams = 0,
        padding: PerimieterParams = 0,
    ):
        self.principal_rect = principal_rect
        self.margin = margin
        self.border = border
        self.padding = padding

        # TODO: Want to invoke this here, but need to redo how tab bars are hidden. The
        # logic currently relies on being able to set `height = 0`.
        # self.validate()

    @property
    def principal_rect(self) -> Rect:
        return self._principal_rect

    @principal_rect.setter
    def principal_rect(self, value: Rect):
        self._principal_rect = value

    @property
    def margin(self) -> Perimeter:
        return self._margin

    @margin.setter
    def margin(self, value: PerimieterParams):
        if isinstance(value, int):
            self._margin = Perimeter(value)
        elif isinstance(value, list):
            self._margin = Perimeter(*value)
        elif isinstance(value, Perimeter):
            self._margin = value
        else:
            raise ValueError("Value must be one of `PerimieterParams` types")

    @property
    def border(self):
        return self._border

    @border.setter
    def border(self, value: PerimieterParams):
        if isinstance(value, int):
            self._border = Perimeter(value)
        elif isinstance(value, list):
            self._border = Perimeter(*value)
        elif isinstance(value, Perimeter):
            self._border = value
        else:
            raise ValueError("Value must be one of `PerimieterParams` types")

    @property
    def padding(self):
        return self._padding

    @padding.setter
    def padding(self, value: PerimieterParams):
        if isinstance(value, int):
            self._padding = Perimeter(value)
        elif isinstance(value, list):
            self._padding = Perimeter(*value)
        elif isinstance(value, Perimeter):
            self._padding = value
        else:
            raise ValueError("Value must be one of `PerimieterParams` types")

    @property
    def margin_rect(self) -> Rect:
        return self.principal_rect

    @property
    def border_rect(self) -> Rect:
        margin_rect = self.margin_rect
        margin = self.margin
        return Rect(
            x=margin_rect.x + margin.left,
            y=margin_rect.y + margin.top,
            w=margin_rect.w - (margin.left + margin.right),
            h=margin_rect.h - (margin.top + margin.bottom),
        )

    @property
    def padding_rect(self) -> Rect:
        border_rect = self.border_rect
        border = self.border
        return Rect(
            x=border_rect.x + border.left,
            y=border_rect.y + border.top,
            w=border_rect.w - (border.left + border.right),
            h=border_rect.h - (border.top + border.bottom),
        )

    @property
    def content_rect(self) -> Rect:
        padding_rect = self.padding_rect
        padding = self.padding
        return Rect(
            x=padding_rect.x + padding.left,
            y=padding_rect.y + padding.top,
            w=padding_rect.w - (padding.left + padding.right),
            h=padding_rect.h - (padding.top + padding.bottom),
        )

    def validate(self):
        content_rect = self.content_rect
        if content_rect.w <= 0 or content_rect.h <= 0:
            raise ValueError(
                "Invalid margin/border/padding values. No space left for content"
            )

    def as_dict(self) -> dict:
        return {
            "principal_rect": self.principal_rect.as_dict(),
            "margin": self.margin.as_dict(),
            "border": self.border.as_dict(),
            "padding": self.padding.as_dict(),
        }

    def __repr__(self):
        return repr(self.principal_rect)
