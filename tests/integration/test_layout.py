# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

import time

import pytest

from qtile_bonsai.core.tree import tree_repr_matches_repr


def test_when_bonsai_layout_is_inactive_and_windows_are_added_in_another_active_layout_then_the_windows_are_captured_as_tabs(
    manager, make_window
):
    manager.to_layout_index(1)
    assert manager.layout.info()["name"] == "columns"

    make_window()
    make_window()

    manager.to_layout_index(0)

    assert tree_repr_matches_repr(
        manager.layout.info()["tree"],
        """
        - tc:1
            - t:2
                - sc.x:3
                    - p:4 | {x: 0, y: 20, w: 800, h: 580}
            - t:5
                - sc.x:6
                    - p:7 | {x: 0, y: 20, w: 800, h: 580}
        """,
    )


def test_when_floating_window_is_unfloated_then_it_is_added_back_to_layout(
    manager, spawn_test_window_cmd
):
    manager.layout.spawn_tab(spawn_test_window_cmd)
    time.sleep(0.5)

    manager.layout.spawn_split(spawn_test_window_cmd, "x")
    time.sleep(0.5)

    manager.window.toggle_floating()
    assert tree_repr_matches_repr(
        manager.layout.info()["tree"],
        """
        - tc:1
            - t:2
                - sc.x:3
                    - p:4 | {x: 0, y: 0, w: 800, h: 600}
        """,
    )

    manager.window.toggle_floating()
    assert tree_repr_matches_repr(
        manager.layout.info()["tree"],
        """
        - tc:1
            - t:2
                - sc.x:3
                    - p:4 | {x: 0, y: 20, w: 800, h: 580}
            - t:6
                - sc.x:7
                    - p:8 | {x: 0, y: 20, w: 800, h: 580}
        """,
    )


class TestStateRestoration:
    def test_when_qtile_config_is_reloaded_then_state_is_restored(
        self, manager, spawn_test_window_cmd
    ):
        bonsai_layout = manager.layout

        bonsai_layout.spawn_tab(spawn_test_window_cmd)
        time.sleep(0.5)

        bonsai_layout.spawn_split(spawn_test_window_cmd, "x")
        time.sleep(0.5)

        bonsai_layout.spawn_split(spawn_test_window_cmd, "y")
        time.sleep(0.5)

        bonsai_layout.spawn_tab(spawn_test_window_cmd, new_level=True)
        time.sleep(0.5)

        manager.reload_config()

        assert tree_repr_matches_repr(
            manager.layout.info()["tree"],
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 0, w: 400, h: 600}
                        - sc.y:6
                            - p:5 | {x: 400, y: 0, w: 400, h: 300}
                            - tc:8
                                - t:9
                                    - sc.x:10
                                        - p:7 | {x: 400, y: 320, w: 400, h: 280}
                                - t:11
                                    - sc.x:12
                                        - p:13 | {x: 400, y: 320, w: 400, h: 280}
            """,
        )

    @pytest.mark.skip(
        reason="""
        Need to figure out some nuances around restarting qtile within a test.
        X11 backend complains about not being able to open socket.
        Wayland backend yells out 'backend does not support restarting.'" 
        """
    )
    def test_when_qtile_is_restarted_then_state_is_restored(
        self, manager, spawn_test_window_cmd
    ):
        bonsai_layout = manager.layout

        bonsai_layout.spawn_tab(spawn_test_window_cmd)
        time.sleep(0.5)

        bonsai_layout.spawn_split(spawn_test_window_cmd, "x")
        time.sleep(0.5)

        bonsai_layout.spawn_split(spawn_test_window_cmd, "y")
        time.sleep(0.5)

        manager.restart()

        assert tree_repr_matches_repr(
            manager.layout.info()["tree"],
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 0, w: 400, h: 600}
                        - sc.y:6
                            - p:5 | {x: 400, y: 0, w: 400, h: 300}
                            - p:7 | {x: 400, y: 300, w: 400, h: 300}
            """,
        )
