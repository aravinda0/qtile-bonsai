# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from __future__ import annotations

from libqtile.config import ScreenRect

from qtile_bonsai.core.geometry import Axis, AxisParam


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
