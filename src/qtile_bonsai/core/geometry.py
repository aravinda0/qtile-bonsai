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
