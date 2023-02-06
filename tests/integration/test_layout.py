# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

from qtile_bonsai.core.tree import repr_matches_repr


def test_when_bonsai_layout_is_inactive_and_windows_are_added_in_another_active_layout_then_the_windows_are_captured_as_tabs(
    manager, make_window
):
    manager.to_layout_index(1)
    assert manager.layout.info()["name"] == "columns"

    make_window()
    make_window()

    manager.to_layout_index(0)

    assert repr_matches_repr(
        manager.layout.info()["tree"],
        """
        - tc:1
            - t:2
                - sc.x:3
                    - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
            - t:5
                - sc.x:6
                    - p:7 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
        """,
    )
