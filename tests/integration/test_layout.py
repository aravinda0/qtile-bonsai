# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

import pytest
from conftest import wait

from qtile_bonsai.core.tree import tree_repr_matches_repr
from tests.integration.utils import make_config_with_bar_and_multiple_screens


@pytest.fixture()
def setup_complex_arrangement(manager, spawn_test_window_cmd):
    """
    Here's the tree that this sets up:

    - tc:1
        - t:2
            - sc.x:3
                - p:4 | {x: 0, y: 20, w: 400, h: 580}
                - sc.y:6
                    - p:5 | {x: 400, y: 20, w: 400, h: 290}
                    - tc:8
                        - t:9
                            - sc.x:10
                                - p:7 | {x: 400, y: 330, w: 400, h: 270}
                        - t:11
                            - sc.x:12
                                - p:13 | {x: 400, y: 330, w: 200, h: 270}
                                - p:14 | {x: 600, y: 330, w: 200, h: 270}
                        - t:15
                            - sc.x:16
                                - p:17 | {x: 400, y: 330, w: 400, h: 270}
        - t:18
            - sc.y:19
                - p:20 | {x: 0, y: 20, w: 800, h: 290}
                - p:21 | {x: 0, y: 310, w: 800, h: 290}
    """
    manager.layout.spawn_tab(spawn_test_window_cmd())
    wait()

    manager.layout.spawn_split(spawn_test_window_cmd(), "x")
    wait()

    manager.layout.spawn_split(spawn_test_window_cmd(), "y")
    wait()

    manager.layout.spawn_tab(spawn_test_window_cmd(), new_level=True)
    wait()

    manager.layout.spawn_split(spawn_test_window_cmd(), "x")
    wait()

    manager.layout.spawn_tab(spawn_test_window_cmd())
    wait()

    manager.layout.spawn_tab(spawn_test_window_cmd(), level=1)
    wait()

    manager.layout.spawn_split(spawn_test_window_cmd(), "y")
    wait()


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
    manager.layout.spawn_tab(spawn_test_window_cmd())
    wait()

    manager.layout.spawn_split(spawn_test_window_cmd(), "x")
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

        manager.layout.spawn_split(spawn_test_window_cmd(), "x")
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


class TestFullScreen:
    def test_when_a_layout_captured_window_is_made_fullscreen_then_we_hide_away_all_other_windows_except_the_fullscreen_one(
        self, manager, spawn_test_window_cmd
    ):
        manager.layout.spawn_tab(spawn_test_window_cmd())
        wait()

        manager.layout.spawn_tab(spawn_test_window_cmd())
        wait()

        manager.layout.spawn_split(spawn_test_window_cmd(), "x")
        wait()

        manager.layout.spawn_split(spawn_test_window_cmd(), "y")
        wait()

        wid = manager.window.info()["id"]

        manager.window.enable_fullscreen()

        state = manager.layout.info()

        def _walk_and_check(node):
            """Makes sure all windows (regular, and internal tab bars) are hidden except
            for the window that is fullscreen.
            """
            if node["type"] == "p":
                if node["wid"] == wid:
                    assert node["is_window_visible"]
                else:
                    assert not node["is_window_visible"]
            elif node["type"] == "tc":
                assert not node["tab_bar"]["is_window_visible"]
            for child in node["children"]:
                _walk_and_check(child)

        _walk_and_check(state["tree"]["root"])


def _custom_default_add_mode_handler(tree):
    if tree.is_empty:
        return tree.tab()
    sc = tree.root.children[0].children[0]
    return tree.split(sc, "x", position="previous")


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

            manager.layout.spawn_split(spawn_test_window_cmd(), "y")
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

            manager.layout.spawn_split(spawn_test_window_cmd(), "x")
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
            [{"window.default_add_mode": "split_x"}],
            indirect=True,
        )
        def test_when_value_is_split_x(
            self, bonsai_layout, manager, spawn_test_window_cmd, make_window
        ):
            make_window()

            manager.layout.spawn_split(spawn_test_window_cmd(), "y")
            wait()

            make_window()

            assert tree_repr_matches_repr(
                manager.layout.tree_repr(),
                """
                - tc:1
                    - t:2
                        - sc.x:6
                            - sc.y:3
                                - p:4 | {x: 0, y: 0, w: 400, h: 300}
                                - p:5 | {x: 0, y: 300, w: 400, h: 300}
                            - p:7 | {x: 400, y: 0, w: 400, h: 600}
                """,
            )

        @pytest.mark.parametrize(
            "bonsai_layout",
            [{"window.default_add_mode": "split_y"}],
            indirect=True,
        )
        def test_when_value_is_split_y(
            self, bonsai_layout, manager, spawn_test_window_cmd, make_window
        ):
            make_window()

            manager.layout.spawn_split(spawn_test_window_cmd(), "x")
            wait()

            make_window()

            assert tree_repr_matches_repr(
                manager.layout.tree_repr(),
                """
                - tc:1
                    - t:2
                        - sc.y:6
                            - sc.x:3
                                - p:4 | {x: 0, y: 0, w: 400, h: 300}
                                - p:5 | {x: 400, y: 0, w: 400, h: 300}
                            - p:7 | {x: 0, y: 300, w: 800, h: 300}
                """,
            )

        @pytest.mark.parametrize(
            "bonsai_layout",
            [{"window.default_add_mode": _custom_default_add_mode_handler}],
            indirect=True,
        )
        def test_when_value_is_callable(
            self, bonsai_layout, manager, spawn_test_window_cmd, make_window
        ):
            make_window()
            make_window()
            make_window()

            assert tree_repr_matches_repr(
                manager.layout.tree_repr(),
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - p:6 | {x: 0, y: 0, w: 400, h: 600}
                            - p:5 | {x: 400, y: 0, w: 200, h: 600}
                            - p:4 | {x: 600, y: 0, w: 200, h: 600}
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
            manager.layout.spawn_split(spawn_test_window_cmd(), "x")
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

    class TestTabBarHideL1WhenBonsaiBarOnScreen:
        @pytest.mark.parametrize(
            "qtile_config",
            [
                make_config_with_bar_and_multiple_screens(
                    layout_config={
                        "tab_bar.hide_L1_when_bonsai_bar_on_screen": True,
                        "tab_bar.height": 20,
                    }
                )
            ],
            indirect=True,
        )
        def test_when_true(self, qtile_config, manager, make_window):
            # Put group `a` on the first screen, which has the widget. The L1 bar should
            # be collapsed.
            manager.group["a"].toscreen(0)
            manager.to_screen(0)
            make_window()
            make_window()

            assert (
                manager.layout.info()["tree"]["root"]["tab_bar"]["box"][
                    "principal_rect"
                ]["h"]
                == 0
            )

            # Move group `a` to the 2nd screen, which does not have our widget. The L1
            # bar should now appear.
            manager.group["a"].toscreen(1)
            manager.to_screen(1)

            assert (
                manager.layout.info()["tree"]["root"]["tab_bar"]["box"][
                    "principal_rect"
                ]["h"]
                == 20
            )

            # Back to screen 1 and it should disappear again.
            manager.group["a"].toscreen(0)
            manager.to_screen(0)

            assert (
                manager.layout.info()["tree"]["root"]["tab_bar"]["box"][
                    "principal_rect"
                ]["h"]
                == 0
            )

        @pytest.mark.parametrize(
            "qtile_config",
            [
                make_config_with_bar_and_multiple_screens(
                    layout_config={
                        "tab_bar.hide_L1_when_bonsai_bar_on_screen": False,
                        "tab_bar.height": 20,
                    }
                )
            ],
            indirect=True,
        )
        def test_when_false(self, qtile_config, manager, make_window):
            # Put group `a` on the first screen, which has the widget. The L1 bar should
            # still be shown despite the widget being present.
            manager.group["a"].toscreen(0)
            manager.to_screen(0)
            make_window()
            make_window()

            assert (
                manager.layout.info()["tree"]["root"]["tab_bar"]["box"][
                    "principal_rect"
                ]["h"]
                == 20
            )

            # Move group `a` to the 2nd screen, which does not have our widget. The L1
            # bar should continue to appear.
            manager.group["a"].toscreen(1)
            manager.to_screen(1)

            assert (
                manager.layout.info()["tree"]["root"]["tab_bar"]["box"][
                    "principal_rect"
                ]["h"]
                == 20
            )


class TestStateRestoration:
    def test_when_qtile_config_is_reloaded_then_state_is_restored(
        self, manager, spawn_test_window_cmd
    ):
        bonsai_layout = manager.layout

        bonsai_layout.spawn_tab(spawn_test_window_cmd())
        wait()

        bonsai_layout.spawn_split(spawn_test_window_cmd(), "x")
        wait()

        bonsai_layout.spawn_split(spawn_test_window_cmd(), "y")
        wait()

        bonsai_layout.spawn_tab(spawn_test_window_cmd(), new_level=True)
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

        bonsai_layout.spawn_tab(spawn_test_window_cmd())
        wait()

        bonsai_layout.spawn_split(spawn_test_window_cmd(), "x")
        wait()

        bonsai_layout.spawn_split(spawn_test_window_cmd(), "y")
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


class TestContainerSelectMode:
    def test_split_on_sc(self, manager, spawn_test_window_cmd):
        manager.layout.spawn_tab(spawn_test_window_cmd())
        wait()

        manager.layout.spawn_split(spawn_test_window_cmd(), "y")
        wait()

        manager.layout.spawn_split(spawn_test_window_cmd(), "x")
        wait()

        manager.layout.toggle_container_select_mode()
        manager.layout.select_container_outer()

        manager.layout.spawn_split(spawn_test_window_cmd(), "y")
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
        manager.layout.spawn_tab(spawn_test_window_cmd())
        wait()

        manager.layout.spawn_split(spawn_test_window_cmd(), "y")
        wait()

        manager.layout.spawn_split(spawn_test_window_cmd(), "x")
        wait()

        manager.layout.toggle_container_select_mode()
        manager.layout.select_container_outer()

        manager.layout.spawn_tab(spawn_test_window_cmd(), new_level=True)
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
        manager.layout.spawn_tab(spawn_test_window_cmd())
        wait()

        manager.layout.toggle_container_select_mode()

        make_window()

        assert manager.layout.info()["interaction_mode"] == "normal"


def test_focus_nth_tab(setup_complex_arrangement, manager):
    """
    Reference:

    - tc:1
        - t:2
            - sc.x:3
                - p:4 | {x: 0, y: 20, w: 400, h: 580}
                - sc.y:6
                    - p:5 | {x: 400, y: 20, w: 400, h: 290}
                    - tc:8
                        - t:9
                            - sc.x:10
                                - p:7 | {x: 400, y: 330, w: 400, h: 270}
                        - t:11
                            - sc.x:12
                                - p:13 | {x: 400, y: 330, w: 200, h: 270}
                                - p:14 | {x: 600, y: 330, w: 200, h: 270}
                        - t:15
                            - sc.x:16
                                - p:17 | {x: 400, y: 330, w: 400, h: 270}
        - t:18
            - sc.y:19
                - p:20 | {x: 0, y: 20, w: 800, h: 290}
                - p:21 | {x: 0, y: 310, w: 800, h: 290}
    """
    manager.switch_window(1)  # 1-indexed
    assert manager.layout.info()["focused_pane_id"] == 4

    manager.layout.focus_nth_tab(2)
    assert manager.layout.info()["focused_pane_id"] == 21

    manager.layout.focus_nth_tab(1, level=1)
    assert manager.layout.info()["focused_pane_id"] == 4

    manager.switch_window(3)
    assert manager.layout.info()["focused_pane_id"] == 7

    manager.layout.focus_nth_tab(3)
    assert manager.layout.info()["focused_pane_id"] == 17

    manager.layout.focus_nth_tab(2, level=-1)
    assert manager.layout.info()["focused_pane_id"] == 14

    manager.layout.focus_nth_tab(2, level=1)
    assert manager.layout.info()["focused_pane_id"] == 21

    # Bad level -> no-op
    manager.layout.focus_nth_tab(1, level=100)
    assert manager.layout.info()["focused_pane_id"] == 21

    # Bad index -> no-op
    manager.layout.focus_nth_tab(100, level=1)
    assert manager.layout.info()["focused_pane_id"] == 21


class TestFocusNthWindow:
    def test_focus_nth_window(self, setup_complex_arrangement, manager):
        """
        Reference:

        - tc:1
            - t:2
                - sc.x:3
                    - p:4 | {x: 0, y: 20, w: 400, h: 580}
                    - sc.y:6
                        - p:5 | {x: 400, y: 20, w: 400, h: 290}
                        - tc:8
                            - t:9
                                - sc.x:10
                                    - p:7 | {x: 400, y: 330, w: 400, h: 270}
                            - t:11
                                - sc.x:12
                                    - p:13 | {x: 400, y: 330, w: 200, h: 270}
                                    - p:14 | {x: 600, y: 330, w: 200, h: 270}
                            - t:15
                                - sc.x:16
                                    - p:17 | {x: 400, y: 330, w: 400, h: 270}
            - t:18
                - sc.y:19
                    - p:20 | {x: 0, y: 20, w: 800, h: 290}
                    - p:21 | {x: 0, y: 310, w: 800, h: 290}
        """
        manager.switch_window(1)  # 1-indexed
        assert manager.layout.info()["focused_pane_id"] == 4

        manager.layout.focus_nth_window(2)
        assert manager.layout.info()["focused_pane_id"] == 5

        manager.layout.focus_nth_window(5)
        assert manager.layout.info()["focused_pane_id"] == 14

        manager.layout.focus_nth_tab(2, level=1)
        manager.layout.focus_nth_window(2, ignore_inactive_tabs_at_levels=[1])
        assert manager.layout.info()["focused_pane_id"] == 21

        manager.layout.focus_nth_window(1, ignore_inactive_tabs_at_levels=[1])
        assert manager.layout.info()["focused_pane_id"] == 20

        manager.layout.focus_nth_window(3, ignore_inactive_tabs_at_levels=[2])
        assert manager.layout.info()["focused_pane_id"] == 13

        # Bad index -> no-op
        manager.layout.focus_nth_window(100)
        assert manager.layout.info()["focused_pane_id"] == 13

    def test_when_3_levels_and_only_level_2_inactive_tabs_not_ignored_but_levels_are(
        self, manager, spawn_test_window_cmd
    ):
        """
        Reference:

        - tc:1
            - t:2
                - sc.x:3
                    - p:4 | {x: 0, y: 20, w: 800, h: 580}
            - t:5
                - sc.x:6
                    - p:7 | {x: 0, y: 20, w: 400, h: 580}
                    - sc.y:9
                        - p:8 | {x: 400, y: 20, w: 400, h: 290}
                        - tc:11
                            - t:12
                                - sc.x:13
                                    - p:10 | {x: 400, y: 330, w: 400, h: 270}
                            - t:14
                                - sc.x:15
                                    - p:16 | {x: 400, y: 330, w: 200, h: 270}
                                    - sc.y:18
                                        - p:17 | {x: 600, y: 330, w: 200, h: 135}
                                        - tc:20
                                            - t:21
                                                - sc.x:22
                                                    - p:19 | {x: 600, y: 485, w: 200, h: 115}
                                            - t:23
                                                - sc.x:24
                                                    - p:25 | {x: 600, y: 485, w: 200, h: 115}
                            - t:26
                                - sc.x:27
                                    - p:28 | {x: 400, y: 330, w: 400, h: 270}
            - t:29
                - sc.x:30
                    - p:31 | {x: 0, y: 20, w: 800, h: 580}
        """
        manager.layout.spawn_tab(spawn_test_window_cmd())
        wait()

        manager.layout.spawn_tab(spawn_test_window_cmd())
        wait()

        manager.layout.spawn_split(spawn_test_window_cmd(), "x")
        wait()

        manager.layout.spawn_split(spawn_test_window_cmd(), "y")
        wait()

        manager.layout.spawn_tab(spawn_test_window_cmd(), new_level=True)
        wait()

        manager.layout.spawn_split(spawn_test_window_cmd(), "x")
        wait()

        manager.layout.spawn_split(spawn_test_window_cmd(), "y")
        wait()

        manager.layout.spawn_tab(spawn_test_window_cmd(), new_level=True)
        wait()

        manager.layout.spawn_tab(spawn_test_window_cmd(), level=2)
        wait()

        manager.layout.spawn_tab(spawn_test_window_cmd(), level=1)
        wait()

        # ----------

        manager.switch_window(5)  # 1-indexed
        assert manager.layout.info()["focused_pane_id"] == 16

        # `p:10` is in a background tab. But we should still be able to select it as
        # level 2 doesn't appear in our `ignore_inactive_tabs_at_levels` and its
        # ancestor tabs that do appear in it are not inactive.
        manager.layout.focus_nth_window(3, ignore_inactive_tabs_at_levels=[1, 3])
        assert manager.layout.info()["focused_pane_id"] == 10
