# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

import pytest
from conftest import wait

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
        manager.layout.tree_repr(),
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
    wait()

    manager.layout.spawn_split(spawn_test_window_cmd, "x")
    wait()

    manager.window.toggle_floating()
    assert tree_repr_matches_repr(
        manager.layout.tree_repr(),
        """
        - tc:1
            - t:2
                - sc.x:3
                    - p:4 | {x: 0, y: 0, w: 800, h: 600}
        """,
    )

    manager.window.toggle_floating()
    assert tree_repr_matches_repr(
        manager.layout.tree_repr(),
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


class TestSpawnSplit:
    def test_when_tree_is_empty_then_split_still_adds_first_window_as_tab(
        self, manager, spawn_test_window_cmd
    ):
        assert manager.layout.tree_repr() == "<empty>"

        manager.layout.spawn_split(spawn_test_window_cmd, "x")
        wait()

        assert tree_repr_matches_repr(
            manager.layout.tree_repr(),
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 0, w: 800, h: 600}
            """,
        )


class TestConfigOptions:
    class TestWindowDefaultAddMode:
        @pytest.mark.parametrize(
            "bonsai_layout",
            [{"window.default_add_mode": "match_previous"}],
            indirect=True,
        )
        def test_when_value_is_match_previous(
            self, bonsai_layout, manager, spawn_test_window_cmd, make_window
        ):
            make_window()

            manager.layout.spawn_split(spawn_test_window_cmd, "y")
            wait()

            make_window()

            assert tree_repr_matches_repr(
                manager.layout.tree_repr(),
                """
                - tc:1
                    - t:2
                        - sc.y:3
                            - p:4 | {x: 0, y: 0, w: 800, h: 200}
                            - p:5 | {x: 0, y: 200, w: 800, h: 200}
                            - p:6 | {x: 0, y: 400, w: 800, h: 200}
                """,
            )

        @pytest.mark.parametrize(
            "bonsai_layout",
            [{"window.default_add_mode": "tab"}],
            indirect=True,
        )
        def test_when_value_is_tab(
            self, bonsai_layout, manager, spawn_test_window_cmd, make_window
        ):
            make_window()

            manager.layout.spawn_split(spawn_test_window_cmd, "x")
            wait()

            make_window()

            assert tree_repr_matches_repr(
                manager.layout.tree_repr(),
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - p:4 | {x: 0, y: 20, w: 400, h: 580}
                            - p:5 | {x: 400, y: 20, w: 400, h: 580}
                    - t:6
                        - sc.x:7
                            - p:8 | {x: 0, y: 20, w: 800, h: 580}
                """,
            )

        @pytest.mark.parametrize(
            "bonsai_layout",
            [{"window.default_add_mode": "match_previous"}],
            indirect=True,
        )
        def test_when_tree_is_empty_and_first_window_was_added_as_a_tab_but_from_a_split_request_then_match_previous_still_respects_that_previous_request_was_for_a_split(
            self,
            bonsai_layout,
            manager,
            spawn_test_window_cmd,
            make_window,
        ):
            manager.layout.spawn_split(spawn_test_window_cmd, "x")
            wait()

            # This should get added as an x-split since the last request was for an
            # x-split.
            make_window()

            assert tree_repr_matches_repr(
                manager.layout.tree_repr(),
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - p:4 | {x: 0, y: 0, w: 400, h: 600}
                            - p:5 | {x: 400, y: 0, w: 400, h: 600}
                """,
            )


class TestStateRestoration:
    def test_when_qtile_config_is_reloaded_then_state_is_restored(
        self, manager, spawn_test_window_cmd
    ):
        bonsai_layout = manager.layout

        bonsai_layout.spawn_tab(spawn_test_window_cmd)
        wait()

        bonsai_layout.spawn_split(spawn_test_window_cmd, "x")
        wait()

        bonsai_layout.spawn_split(spawn_test_window_cmd, "y")
        wait()

        bonsai_layout.spawn_tab(spawn_test_window_cmd, new_level=True)
        wait()

        manager.reload_config()

        assert tree_repr_matches_repr(
            manager.layout.tree_repr(),
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
        wait()

        bonsai_layout.spawn_split(spawn_test_window_cmd, "x")
        wait()

        bonsai_layout.spawn_split(spawn_test_window_cmd, "y")
        wait()

        manager.restart()

        assert tree_repr_matches_repr(
            manager.layout.tree_repr(),
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


class TestBranchSelectMode:
    def test_split_on_sc(self, manager, spawn_test_window_cmd):
        manager.layout.spawn_tab(spawn_test_window_cmd)
        wait()

        manager.layout.spawn_split(spawn_test_window_cmd, "y")
        wait()

        manager.layout.spawn_split(spawn_test_window_cmd, "x")
        wait()

        manager.layout.toggle_branch_select_mode()
        manager.layout.select_branch_out()

        manager.layout.spawn_split(spawn_test_window_cmd, "y")
        wait()

        assert tree_repr_matches_repr(
            manager.layout.tree_repr(),
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0, y: 0, w: 800, h: 200}
                        - sc.x:6
                            - p:5 | {x: 0, y: 200, w: 400, h: 200}
                            - p:7 | {x: 400, y: 200, w: 400, h: 200}
                        - p:8 | {x: 0, y: 400, w: 800, h: 200}
            """,
        )

    def test_subtab_on_sc(self, manager, spawn_test_window_cmd):
        manager.layout.spawn_tab(spawn_test_window_cmd)
        wait()

        manager.layout.spawn_split(spawn_test_window_cmd, "y")
        wait()

        manager.layout.spawn_split(spawn_test_window_cmd, "x")
        wait()

        manager.layout.toggle_branch_select_mode()
        manager.layout.select_branch_out()

        manager.layout.spawn_tab(spawn_test_window_cmd, new_level=True)
        wait()

        assert tree_repr_matches_repr(
            manager.layout.tree_repr(),
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0, y: 0, w: 800, h: 300}
                        - tc:8
                            - t:9
                                - sc.x:6
                                    - p:5 | {x: 0, y: 320, w: 400, h: 280}
                                    - p:7 | {x: 400, y: 320, w: 400, h: 280}
                            - t:10
                                - sc.x:11
                                    - p:12 | {x: 0, y: 320, w: 800, h: 280}
            """,
        )

    def test_when_a_new_window_is_added_implicitly_then_interaction_mode_reverts_to_normal_mode(
        self, manager, spawn_test_window_cmd, make_window
    ):
        manager.layout.spawn_tab(spawn_test_window_cmd)
        wait()

        manager.layout.toggle_branch_select_mode()

        make_window()

        assert manager.layout.info()["interaction_mode"] == "normal"
