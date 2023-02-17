# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

import pytest
from qtile_bonsai.core.geometry import Rect


class TestRect:
    class TestSplit:
        @pytest.mark.parametrize(
            ("rect", "axis", "expected1", "expected2"),
            [
                (Rect(0, 0, 100, 100), "x", Rect(0, 0, 50, 100), Rect(50, 0, 50, 100)),
                (Rect(0, 0, 100, 100), "y", Rect(0, 0, 100, 50), Rect(0, 50, 100, 50)),
            ],
        )
        def test_returns_rects_that_do_not_have_overlapping_coordinates(
            self, rect, axis, expected1, expected2
        ):
            r1, r2 = rect.split(axis)

            assert r1 == expected1
            assert r2 == expected2

        @pytest.mark.parametrize(
            ("rect", "axis", "ratio", "expected1", "expected2"),
            [
                (
                    Rect(0, 0, 100, 100),
                    "x",
                    0.1,
                    Rect(0, 0, 10, 100),
                    Rect(10, 0, 90, 100),
                ),
                (
                    Rect(0, 0, 100, 100),
                    "y",
                    0.8,
                    Rect(0, 0, 100, 80),
                    Rect(0, 80, 100, 20),
                ),
            ],
        )
        def test_when_ratio_is_provided_then_rect_is_split_accordingly(
            self, rect, axis, ratio, expected1, expected2
        ):
            r1, r2 = rect.split(axis, ratio)

            assert r1 == expected1
            assert r2 == expected2
