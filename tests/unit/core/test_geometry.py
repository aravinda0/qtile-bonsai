# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

import pytest

from qtile_bonsai.core.geometry import Box, Rect


@pytest.fixture
def layered_box():
    return Box(
        principal_rect=Rect(100, 100, 400, 300),
        margin=[10, 20, 30, 40],
        border=[1, 2, 3, 4],
        padding=[15, 25, 35, 45],
    )


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


class TestBox:
    def test_margin_rect_is_equal_to_principal_rect(self, layered_box: Box):
        assert layered_box.margin_rect == layered_box.principal_rect

    def test_border_rect_includes_content_padding_border(self, layered_box: Box):
        assert layered_box.border_rect == Rect(140, 110, 340, 260)

    def test_padding_rect_includes_content_padding(self, layered_box: Box):
        assert layered_box.padding_rect == Rect(144, 111, 334, 256)

    def test_content_rect_includes_content_only(self, layered_box: Box):
        assert layered_box.content_rect == Rect(189, 126, 264, 206)

    @pytest.mark.parametrize(
        ("margin", "border", "padding"),
        [
            (80, 0, 0),
            (0, 80, 0),
            (0, 0, 80),
            (80, 80, 80),
        ],
    )
    def test_raises_error_on_invalid_perimeters(self, margin, border, padding):
        box = Box(
            Rect(100, 100, 100, 100),
            margin=margin,
            border=border,
            padding=padding,
        )
        err_msg = "Invalid margin/border/padding values. No space left for content"
        with pytest.raises(ValueError, match=err_msg):
            box.validate()
