# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from __future__ import annotations

import typing
from typing import Literal

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


def validate_unit_range(value: float, field_name: str):
    if not (0 <= value <= 1):
        raise ValueError(f"Value of `{field_name}` must be between 0 and 1 inclusive.")
