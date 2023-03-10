# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from unittest import mock

import pytest
from qtile_bonsai.core.geometry import Rect
from qtile_bonsai.core.tree import (
    Pane,
    Tab,
    TabContainer,
    Tree,
    TreeEvent,
    tree_matches_repr,
)


@pytest.fixture()
def tree() -> Tree:
    return Tree(400, 300)


@pytest.fixture()
def make_tree_with_subscriber(tree):
    def _make_tree_with_subscriber(event: TreeEvent):
        callback = mock.Mock()
        tree.subscribe(event, callback)
        return tree, callback

    return _make_tree_with_subscriber


class TestIsEmpty:
    def test_new_tree_instance_is_empty(self, tree):
        assert tree.is_empty

    def test_tree_with_panes_is_not_empty(self, tree):
        tree.tab()

        assert not tree.is_empty


class TestSplit:
    def test_returns_correct_pane(self, tree):
        p1 = tree.tab()

        p2 = tree.split(p1, "x")
        p3 = tree.split(p2, "x")

        assert isinstance(p2, Pane)
        assert p2.id == 5

        assert isinstance(p3, Pane)
        assert p3.id == 6

    def test_split_along_x_axis(self, tree):
        p1 = tree.tab()

        tree.split(p1, "x")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 200, h: 280}
                        - p:5 | {x: 200, y: 20, w: 200, h: 280}
            """,
        )

    def test_split_along_y_axis(self, tree):
        p1 = tree.tab()

        tree.split(p1, "y")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0, y: 20, w: 400, h: 140}
                        - p:5 | {x: 0, y: 160, w: 400, h: 140}
            """,
        )

    def test_subsequent_splits_are_added_under_the_same_split_container(self, tree):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")

        tree.split(p2, "x")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 200, h: 280}
                        - p:5 | {x: 200, y: 20, w: 100, h: 280}
                        - p:6 | {x: 300, y: 20, w: 100, h: 280}
            """,
        )

    def test_when_there_are_already_splits_present_then_new_splits_happen_at_the_requested_position(
        self, tree
    ):
        p1 = tree.tab()
        tree.split(p1, "x")

        tree.split(p1, "x")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 100, h: 280}
                        - p:6 | {x: 100, y: 20, w: 100, h: 280}
                        - p:5 | {x: 200, y: 20, w: 200, h: 280}
            """,
        )

    def test_can_split_by_arbitrary_ratio(self, tree):
        p1 = tree.tab()

        tree.split(p1, "x", 0.8)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 320, h: 280}
                        - p:5 | {x: 320, y: 20, w: 80, h: 280}
            """,
        )

    @pytest.mark.parametrize("ratio", [-1, -0.1, 1.1, 10])
    def test_when_invalid_ratio_provided_should_raise_error(self, tree, ratio):
        p1 = tree.tab()

        err_msg = "Value of `ratio` must be between 0 and 1 inclusive."
        with pytest.raises(ValueError, match=err_msg):
            tree.split(p1, "x", ratio)

    def test_subscribers_are_notified_of_added_nodes(self, tree):
        callback = mock.Mock()
        tree.subscribe(TreeEvent.node_added, callback)

        p1 = tree.tab()
        sc1, t1, tc1 = p1.get_ancestors()

        p2 = tree.split(p1, "x")

        p3 = tree.split(p2, "y")
        sc2 = p3.parent

        p4 = tree.split(p3, "x")
        sc3 = p4.parent

        p5 = tree.split(p4, "y")
        sc4 = p5.parent

        p6 = tree.split(p5, "y")

        assert callback.mock_calls == [
            mock.call([tc1, t1, sc1, p1]),
            mock.call([p2]),
            mock.call([sc2, p3]),
            mock.call([sc3, p4]),
            mock.call([sc4, p5]),
            mock.call([p6]),
        ]


class TestNestedSplits:
    def test_when_y_split_happens_on_an_x_split_then_resulting_splits_are_placed_under_new_y_split_container(
        self, tree
    ):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")

        tree.split(p2, "y")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 200, h: 280}
                        - sc.y:6
                            - p:5 | {x: 200, y: 20, w: 200, h: 140}
                            - p:7 | {x: 200, y: 160, w: 200, h: 140}
            """,
        )

    def test_when_x_split_happens_on_a_y_split_then_resulting_splits_are_placed_under_new_x_split_container(
        self, tree
    ):
        p1 = tree.tab()
        p2 = tree.split(p1, "y")

        tree.split(p2, "x")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0, y: 20, w: 400, h: 140}
                        - sc.x:6
                            - p:5 | {x: 0, y: 160, w: 200, h: 140}
                            - p:7 | {x: 200, y: 160, w: 200, h: 140}
            """,
        )

    def test_nested_x_split(self, tree):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")
        p3 = tree.split(p2, "y")

        tree.split(p3, "x")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 200, h: 280}
                        - sc.y:6
                            - p:5 | {x: 200, y: 20, w: 200, h: 140}
                            - sc.x:8
                                - p:7 | {x: 200, y: 160, w: 100, h: 140}
                                - p:9 | {x: 300, y: 160, w: 100, h: 140}
            """,
        )

    def test_nested_y_split(self, tree):
        p1 = tree.tab()
        p2 = tree.split(p1, "y")
        p3 = tree.split(p2, "x")

        tree.split(p3, "y")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0, y: 20, w: 400, h: 140}
                        - sc.x:6
                            - p:5 | {x: 0, y: 160, w: 200, h: 140}
                            - sc.y:8
                                - p:7 | {x: 200, y: 160, w: 200, h: 70}
                                - p:9 | {x: 200, y: 230, w: 200, h: 70}
            """,
        )


class TestAddTab:
    class TestParameterValidity:
        def test_when_tree_is_empty_and_pane_reference_is_provided_then_raises_error(
            self, tree
        ):
            dummy_pane = Pane(principal_rect=Rect(0, 0, 1, 1))

            err_msg = "The tree is empty. The provided arguments are invalid."
            with pytest.raises(ValueError, match=err_msg):
                tree.tab(at_pane=dummy_pane)

        def test_when_tree_is_empty_and_new_level_is_requested_then_raises_error(
            self, tree
        ):
            err_msg = "The tree is empty. The provided arguments are invalid."
            with pytest.raises(ValueError, match=err_msg):
                tree.tab(new_level=True)

        def test_when_tree_is_empty_and_level_is_specified_then_raises_error(
            self, tree
        ):
            err_msg = "The tree is empty. The provided arguments are invalid."
            with pytest.raises(ValueError, match=err_msg):
                tree.tab(level=2)

        def test_when_new_level_is_requested_and_pane_reference_not_provided_then_raises_error(
            self, tree
        ):
            tree.tab()

            err_msg = (
                "`new_level` requires a reference `at_pane` under which to add tabs"
            )
            with pytest.raises(ValueError, match=err_msg):
                tree.tab(new_level=True)

        def test_when_level_specified_but_pane_reference_not_provided_then_raises_error(
            self, tree
        ):
            tree.tab()

            err_msg = "`level` requires a reference `at_pane`"
            with pytest.raises(ValueError, match=err_msg):
                tree.tab(level=2)

        @pytest.mark.parametrize("level", [-5, -1, 0])
        def test_when_level_specified_but_is_less_than_1_then_raises_error(
            self, tree, level
        ):
            p1 = tree.tab()

            err_msg = "`level` must be 1 or higher"
            with pytest.raises(ValueError, match=err_msg):
                tree.tab(p1, level=level)

        def test_when_level_specified_but_is_more_than_tree_level_then_raises_error(
            self, tree
        ):
            p1 = tree.tab()
            tree.tab(p1, new_level=True)
            tree.tab(p1, new_level=True)

            err_msg = "`4` is an invalid level. The tree currently only has 3 levels."
            with pytest.raises(ValueError, match=err_msg):
                tree.tab(p1, level=4)

    def test_pane_is_returned(self, tree):
        pane = tree.tab()

        assert isinstance(pane, Pane)

    def test_add_tab_to_empty_tree(self, tree):
        tree.tab()

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 400, h: 280}
            """,
        )

    def test_add_tab_to_non_empty_tree(self, tree):
        tree.tab()

        tree.tab()

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 400, h: 280}
                - t:5
                    - sc.x:6
                        - p:7 | {x: 0, y: 20, w: 400, h: 280}
            """,
        )

    def test_tab_container_has_active_tab(self, tree):
        p1 = tree.tab()

        assert tree.is_visible(p1)

    def test_add_tab_at_specified_pane(self, tree):
        tree.tab()
        p2 = tree.tab()
        tree.tab()

        # Current behvavior adds tab at end of provided pane's level of tabs.
        tree.tab(p2)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 400, h: 280}
                - t:5
                    - sc.x:6
                        - p:7 | {x: 0, y: 20, w: 400, h: 280}
                - t:8
                    - sc.x:9
                        - p:10 | {x: 0, y: 20, w: 400, h: 280}
                - t:11
                    - sc.x:12
                        - p:13 | {x: 0, y: 20, w: 400, h: 280}
            """,
        )

    def test_given_a_tree_with_nested_tab_levels_when_a_tab_is_added_without_providing_a_pane_reference_then_the_new_tab_is_added_at_the_topmost_level(
        self, tree
    ):
        p1 = tree.tab()
        tree.tab(p1, new_level=True)

        tree.tab()

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:5
                            - t:6
                                - sc.x:7
                                    - p:4 | {x: 0, y: 40, w: 400, h: 260}
                            - t:8
                                - sc.x:9
                                    - p:10 | {x: 0, y: 40, w: 400, h: 260}
                - t:11
                    - sc.x:12
                        - p:13 | {x: 0, y: 20, w: 400, h: 280}
            """,
        )

    def test_given_a_tree_with_nested_tab_levels_when_a_tab_is_added_at_a_pane_at_nested_tab_level_and_level_is_not_specified_then_tab_is_added_at_deepest_tab_level_of_the_pane(
        self, tree
    ):
        p1 = tree.tab()
        tree.tab(p1, new_level=True)

        tree.tab(p1)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:5
                            - t:6
                                - sc.x:7
                                    - p:4 | {x: 0, y: 40, w: 400, h: 260}
                            - t:8
                                - sc.x:9
                                    - p:10 | {x: 0, y: 40, w: 400, h: 260}
                            - t:11
                                - sc.x:12
                                    - p:13 | {x: 0, y: 40, w: 400, h: 260}
            """,
        )

    def test_add_tab_at_new_level(self, tree):
        p1 = tree.tab()

        tree.tab(p1, new_level=True)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:5
                            - t:6
                                - sc.x:7
                                    - p:4 | {x: 0, y: 40, w: 400, h: 260}
                            - t:8
                                - sc.x:9
                                    - p:10 | {x: 0, y: 40, w: 400, h: 260}
            """,
        )

    def test_nested_tab_containers_have_active_tab(self, tree):
        p1 = tree.tab()
        p2 = tree.tab(p1, new_level=True)

        assert tree.is_visible(p2)

    def test_add_tab_at_multiple_new_levels(self, tree):
        p1 = tree.tab()

        p2 = tree.tab(p1, new_level=True)
        p3 = tree.tab(p2, new_level=True)
        tree.tab(p3, new_level=True)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:5
                            - t:6
                                - sc.x:7
                                    - p:4 | {x: 0, y: 40, w: 400, h: 260}
                            - t:8
                                - sc.x:9
                                    - tc:11
                                        - t:12
                                            - sc.x:13
                                                - p:10 | {x: 0, y: 60, w: 400, h: 240}
                                        - t:14
                                            - sc.x:15
                                                - tc:17
                                                    - t:18
                                                        - sc.x:19
                                                            - p:16 | {x: 0, y: 80, w: 400, h: 220}
                                                    - t:20
                                                        - sc.x:21
                                                            - p:22 | {x: 0, y: 80, w: 400, h: 220}
            """,
        )

    def test_add_tab_at_new_level_in_split(self, tree):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")

        tree.tab(p2, new_level=True)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 200, h: 280}
                        - tc:6
                            - t:7
                                - sc.x:8
                                    - p:5 | {x: 200, y: 40, w: 200, h: 260}
                            - t:9
                                - sc.x:10
                                    - p:11 | {x: 200, y: 40, w: 200, h: 260}
            """,
        )

    def test_add_tab_at_new_level_in_multiple_splits(self, tree):
        p1 = tree.tab()
        p2 = tree.split(p1, "y")
        tree.split(p1, "x")

        tree.tab(p2, new_level=True)
        tree.tab(p1, new_level=True)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - sc.x:6
                            - tc:14
                                - t:15
                                    - sc.x:16
                                        - p:4 | {x: 0, y: 40, w: 200, h: 120}
                                - t:17
                                    - sc.x:18
                                        - p:19 | {x: 0, y: 40, w: 200, h: 120}
                            - p:7 | {x: 200, y: 20, w: 200, h: 140}
                        - tc:8
                            - t:9
                                - sc.x:10
                                    - p:5 | {x: 0, y: 180, w: 400, h: 120}
                            - t:11
                                - sc.x:12
                                    - p:13 | {x: 0, y: 180, w: 400, h: 120}
            """,
        )

    def test_add_tab_at_new_level_at_split_in_nested_tab_level(self, tree):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")
        p3 = tree.tab(p2, new_level=True)
        p4 = tree.split(p3, "y")

        tree.tab(p4, new_level=True)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 200, h: 280}
                        - tc:6
                            - t:7
                                - sc.x:8
                                    - p:5 | {x: 200, y: 40, w: 200, h: 260}
                            - t:9
                                - sc.y:10
                                    - p:11 | {x: 200, y: 40, w: 200, h: 130}
                                    - tc:13
                                        - t:14
                                            - sc.x:15
                                                - p:12 | {x: 200, y: 190, w: 200, h: 110}
                                        - t:16
                                            - sc.x:17
                                                - p:18 | {x: 200, y: 190, w: 200, h: 110}
            """,
        )

    def test_add_tab_at_arbitrary_level(self, tree):
        p1 = tree.tab()
        p2 = tree.tab(p1, new_level=True)
        tree.tab(p2, new_level=True)

        # Before this invocation, p1 is at level 2; p2, p3 are at level 3. So if we take
        # p2, we can add at either level 1, level 2 or level 3. We pick level 2.
        tree.tab(p2, level=2)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:5
                            - t:6
                                - sc.x:7
                                    - p:4 | {x: 0, y: 40, w: 400, h: 260}
                            - t:8
                                - sc.x:9
                                    - tc:11
                                        - t:12
                                            - sc.x:13
                                                - p:10 | {x: 0, y: 60, w: 400, h: 240}
                                        - t:14
                                            - sc.x:15
                                                - p:16 | {x: 0, y: 60, w: 400, h: 240}
                            - t:17
                                - sc.x:18
                                    - p:19 | {x: 0, y: 40, w: 400, h: 260}
            """,
        )

    def test_add_tab_at_level_when_different_nest_levels_present_under_different_splits(
        self, tree
    ):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")

        tree.tab(p1, new_level=True)
        p4 = tree.tab(p1, new_level=True)
        tree.tab(p1, new_level=True)

        tree.tab(p2, new_level=True)
        tree.tab(p2, new_level=True)

        # Before this invocation, under two top level split panes, we have 4 levels on
        # the left side and 3 levels on the right side. Adding at p4 at level 2 should
        # only add to the 2nd level under the left pane.
        tree.tab(p4, level=2)

        # Nodes 36, 37, 38 get added.
        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:6
                            - t:7
                                - sc.x:8
                                    - tc:12
                                        - t:13
                                            - sc.x:14
                                                - tc:18
                                                    - t:19
                                                        - sc.x:20
                                                            - p:4 | {x: 0, y: 80, w: 200, h: 220}
                                                    - t:21
                                                        - sc.x:22
                                                            - p:23 | {x: 0, y: 80, w: 200, h: 220}
                                        - t:15
                                            - sc.x:16
                                                - p:17 | {x: 0, y: 60, w: 200, h: 240}
                            - t:9
                                - sc.x:10
                                    - p:11 | {x: 0, y: 40, w: 200, h: 260}
                            - t:36
                                - sc.x:37
                                    - p:38 | {x: 0, y: 40, w: 200, h: 260}
                        - tc:24
                            - t:25
                                - sc.x:26
                                    - tc:30
                                        - t:31
                                            - sc.x:32
                                                - p:5 | {x: 200, y: 60, w: 200, h: 240}
                                        - t:33
                                            - sc.x:34
                                                - p:35 | {x: 200, y: 60, w: 200, h: 240}
                            - t:27
                                - sc.x:28
                                    - p:29 | {x: 200, y: 40, w: 200, h: 260}
            """,
        )

    def test_subscribers_are_notified_of_added_nodes(self, tree):
        callback = mock.Mock()
        tree.subscribe(TreeEvent.node_added, callback)

        p1 = tree.tab()
        sc1, t1, tc1 = p1.get_ancestors()

        p2 = tree.tab(p1)
        sc2, t2, _ = p2.get_ancestors()

        p3 = tree.tab(p2, new_level=True)
        sc3, t3, tc2, _, _, _ = p3.get_ancestors()

        assert callback.mock_calls == [
            mock.call([tc1, t1, sc1, p1]),
            mock.call([t2, sc2, p2]),
            mock.call([tc2, t3, sc3, p3]),
        ]


class TestSplitsUnderTabs:
    def test_x_split_does_not_affect_dimensions_of_other_tabs(self, tree):
        p1 = tree.tab()
        tree.tab()
        p3 = tree.tab()

        tree.split(p1, "x")
        tree.split(p1, "x")
        tree.split(p3, "x")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 100, h: 280}
                        - p:12 | {x: 100, y: 20, w: 100, h: 280}
                        - p:11 | {x: 200, y: 20, w: 200, h: 280}
                - t:5
                    - sc.x:6
                        - p:7 | {x: 0, y: 20, w: 400, h: 280}
                - t:8
                    - sc.x:9
                        - p:10 | {x: 0, y: 20, w: 200, h: 280}
                        - p:13 | {x: 200, y: 20, w: 200, h: 280}
            """,
        )

    def test_y_split_does_not_affect_dimensions_of_other_tabs(self, tree):
        p1 = tree.tab()
        tree.tab()
        p3 = tree.tab()

        tree.split(p1, "y")
        tree.split(p1, "y")
        tree.split(p3, "y")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0, y: 20, w: 400, h: 70}
                        - p:12 | {x: 0, y: 90, w: 400, h: 70}
                        - p:11 | {x: 0, y: 160, w: 400, h: 140}
                - t:5
                    - sc.x:6
                        - p:7 | {x: 0, y: 20, w: 400, h: 280}
                - t:8
                    - sc.y:9
                        - p:10 | {x: 0, y: 20, w: 400, h: 140}
                        - p:13 | {x: 0, y: 160, w: 400, h: 140}
            """,
        )

    def test_x_split_under_nested_tab(self, tree):
        p1 = tree.tab()
        p2 = tree.tab(p1, new_level=True)

        tree.split(p2, "x")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:5
                            - t:6
                                - sc.x:7
                                    - p:4 | {x: 0, y: 40, w: 400, h: 260}
                            - t:8
                                - sc.x:9
                                    - p:10 | {x: 0, y: 40, w: 200, h: 260}
                                    - p:11 | {x: 200, y: 40, w: 200, h: 260}
            """,
        )

    def test_y_split_under_nested_tab(self, tree):
        p1 = tree.tab()
        p2 = tree.tab(p1, new_level=True)

        tree.split(p2, "y")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:5
                            - t:6
                                - sc.x:7
                                    - p:4 | {x: 0, y: 40, w: 400, h: 260}
                            - t:8
                                - sc.y:9
                                    - p:10 | {x: 0, y: 40, w: 400, h: 130}
                                    - p:11 | {x: 0, y: 170, w: 400, h: 130}
            """,
        )

    def test_nested_splits_under_nested_tabs(self, tree):
        p1 = tree.tab()
        p2 = tree.split(p1, "y")
        tree.split(p1, "x")
        p4 = tree.split(p2, "x")

        tree.tab(p1, new_level=True)
        p6 = tree.tab(p4, new_level=True)

        tree.split(p1, "x")
        tree.split(p1, "y")
        tree.split(p6, "x")
        tree.split(p6, "y")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - sc.x:6
                            - tc:10
                                - t:11
                                    - sc.x:12
                                        - sc.y:23
                                            - p:4 | {x: 0, y: 40, w: 100, h: 60}
                                            - p:24 | {x: 0, y: 100, w: 100, h: 60}
                                        - p:22 | {x: 100, y: 40, w: 100, h: 120}
                                - t:13
                                    - sc.x:14
                                        - p:15 | {x: 0, y: 40, w: 200, h: 120}
                            - p:7 | {x: 200, y: 20, w: 200, h: 140}
                        - sc.x:8
                            - p:5 | {x: 0, y: 160, w: 200, h: 140}
                            - tc:16
                                - t:17
                                    - sc.x:18
                                        - p:9 | {x: 200, y: 180, w: 200, h: 120}
                                - t:19
                                    - sc.x:20
                                        - sc.y:26
                                            - p:21 | {x: 200, y: 180, w: 100, h: 60}
                                            - p:27 | {x: 200, y: 240, w: 100, h: 60}
                                        - p:25 | {x: 300, y: 180, w: 100, h: 120}
            """,
        )


class TestResize:
    def test_resize_on_x_axis_by_positive_amount(self, tree):
        p1 = tree.tab()
        tree.split(p1, "x")

        tree.resize(p1, "x", 50)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 250, h: 280}
                        - p:5 | {x: 250, y: 20, w: 150, h: 280}
            """,
        )

    def test_resize_on_x_axis_by_negative_amount(self, tree):
        p1 = tree.tab()
        tree.split(p1, "x")

        tree.resize(p1, "x", -50)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 150, h: 280}
                        - p:5 | {x: 150, y: 20, w: 250, h: 280}
            """,
        )

    def test_resize_on_y_axis_by_positive_amount(self, tree):
        p1 = tree.tab()
        tree.split(p1, "y")

        tree.resize(p1, "y", 50)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0, y: 20, w: 400, h: 190}
                        - p:5 | {x: 0, y: 210, w: 400, h: 90}
            """,
        )

    def test_resize_on_y_axis_by_negative_amount(self, tree):
        p1 = tree.tab()
        tree.split(p1, "y")

        tree.resize(p1, "y", -50)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0, y: 20, w: 400, h: 90}
                        - p:5 | {x: 0, y: 110, w: 400, h: 190}
            """,
        )

    def test_given_a_pane_that_is_not_the_last_child_when_resize_happens_on_x_axis_then_the_right_border_is_modified(
        self, tree
    ):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")
        tree.split(p2, "x")

        tree.resize(p2, "x", 50)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 200, h: 280}
                        - p:5 | {x: 200, y: 20, w: 150, h: 280}
                        - p:6 | {x: 350, y: 20, w: 50, h: 280}
            """,
        )

    def test_given_a_pane_that_is_the_last_child_when_resize_happens_on_x_axis_then_the_left_border_is_modified(
        self, tree
    ):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")
        p3 = tree.split(p2, "x")

        tree.resize(p3, "x", 50)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 200, h: 280}
                        - p:5 | {x: 200, y: 20, w: 150, h: 280}
                        - p:6 | {x: 350, y: 20, w: 50, h: 280}
            """,
        )

    def test_given_a_pane_that_is_not_the_last_child_when_resize_happens_on_y_axis_then_the_bottom_border_is_modified(
        self, tree
    ):
        p1 = tree.tab()
        p2 = tree.split(p1, "y")
        tree.split(p2, "y")

        tree.resize(p2, "y", 50)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0, y: 20, w: 400, h: 140}
                        - p:5 | {x: 0, y: 160, w: 400, h: 120}
                        - p:6 | {x: 0, y: 280, w: 400, h: 20}
            """,
        )

    def test_given_a_pane_that_is_the_last_child_when_resize_happens_on_y_axis_then_the_top_border_is_modified(
        self, tree
    ):
        p1 = tree.tab()
        p2 = tree.split(p1, "y")
        p3 = tree.split(p2, "y")

        tree.resize(p3, "y", 50)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0, y: 20, w: 400, h: 140}
                        - p:5 | {x: 0, y: 160, w: 400, h: 120}
                        - p:6 | {x: 0, y: 280, w: 400, h: 20}
            """,
        )

    @pytest.mark.parametrize("axis", ["x", "y"])
    @pytest.mark.parametrize("amount", [50, -50])
    def test_when_lone_top_level_panes_under_top_level_tabs_are_resized_then_it_is_a_no_op(
        self, tree, axis, amount
    ):
        p1 = tree.tab()
        p2 = tree.tab()
        p3 = tree.tab()

        tree.resize(p1, axis, amount)
        tree.resize(p2, axis, amount)
        tree.resize(p3, axis, amount)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 400, h: 280}
                - t:5
                    - sc.x:6
                        - p:7 | {x: 0, y: 20, w: 400, h: 280}
                - t:8
                    - sc.x:9
                        - p:10 | {x: 0, y: 20, w: 400, h: 280}
            """,
        )

    @pytest.mark.parametrize("amount", [50, -50])
    def test_when_top_level_panes_under_root_tab_container_are_resized_against_axis_then_it_is_a_no_op(
        self, tree, amount
    ):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")

        tree.resize(p1, "y", amount)
        tree.resize(p2, "y", amount)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 200, h: 280}
                        - p:5 | {x: 200, y: 20, w: 200, h: 280}
            """,
        )

    class TestResizeInvolvingNestedSplits:
        def test_resizing_nested_pane_along_axis_should_only_affect_the_pane_and_its_sibling(
            self, tree
        ):
            p1 = tree.tab()
            tree.split(p1, "x")
            tree.split(p1, "y")
            p4 = tree.split(p1, "x")
            tree.split(p4, "x")

            # Resizing `p:9` along container axis should only affect `p:9` and `p:10`
            tree.resize(p4, "x", 20)

            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - sc.y:6
                                - sc.x:8
                                    - p:4 | {x: 0, y: 20, w: 100, h: 140}
                                    - p:9 | {x: 100, y: 20, w: 70, h: 140}
                                    - p:10 | {x: 170, y: 20, w: 30, h: 140}
                                - p:7 | {x: 0, y: 160, w: 200, h: 140}
                            - p:5 | {x: 200, y: 20, w: 200, h: 280}
                """,
            )

        def test_resizing_nested_pane_against_axis_should_resize_all_panes_in_enclosing_container_and_sibling_of_the_container(
            self, tree
        ):
            p1 = tree.tab()
            tree.split(p1, "x")
            tree.split(p1, "y")
            p4 = tree.split(p1, "x")
            tree.split(p4, "x")

            # Resizing `p:9` against container axis should affect all panes in enclosing
            # container - `p:4`, `p:9`, `p:10`; and the sibling of the container - `p:7`
            tree.resize(p4, "y", 20)

            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - sc.y:6
                                - sc.x:8
                                    - p:4 | {x: 0, y: 20, w: 100, h: 160}
                                    - p:9 | {x: 100, y: 20, w: 50, h: 160}
                                    - p:10 | {x: 150, y: 20, w: 50, h: 160}
                                - p:7 | {x: 0, y: 180, w: 200, h: 120}
                            - p:5 | {x: 200, y: 20, w: 200, h: 280}
                """,
            )

        @pytest.mark.case_pixel_rounding()
        class TestWhenOperationalSiblingIsContainerBeingGrown:
            def test_should_grow_nested_items_that_are_along_resize_axis_in_proportion_to_their_size_along_that_axis(
                self, tree
            ):
                p1 = tree.tab()
                p2 = tree.split(p1, "x")
                p3 = tree.split(p2, "y")
                tree.split(p3, "x")
                tree.split(p3, "x")

                # Shrinking `p:4` should grow all panes in `sc.y:6`.
                # In `sc.y:6`, those in `sc.x:8` should be grown by fractions of 50
                # proportional to their size. From the 50 amount, `p:7` grows by
                # round(6.25) -> 6, `p:10` grows by round(6.25) -> 6, `p:9` grows by
                # round(12.5) -> 12. The start coordinates are also adjusted.
                # NOTE: We lose 1 pixel here due to the rounding (56 + 56 + 112 = 224).
                # Will revisit this if it accumulates to significance.
                tree.resize(p1, "x", -25)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0, y: 20, w: 175, h: 280}
                                - sc.y:6
                                    - p:5 | {x: 175, y: 20, w: 225, h: 140}
                                    - sc.x:8
                                        - p:7 | {x: 175, y: 160, w: 56, h: 140}
                                        - p:10 | {x: 231, y: 160, w: 56, h: 140}
                                        - p:9 | {x: 287, y: 160, w: 112, h: 140}
                    """,
                )

            def test_should_grow_nested_items_that_are_against_resize_axis_by_the_same_amount(
                self, tree
            ):
                p1 = tree.tab()
                p2 = tree.split(p1, "x")
                p3 = tree.split(p2, "y")
                p4 = tree.split(p3, "x")
                tree.split(p3, "y")
                tree.split(p4, "y")

                # Shrinking `p:4` would grow all panes in `sc.y:6`.
                # Children of `sc.x:8` that are along the resize axis get 20 each.
                # Then children of `sc.y:10` and `sc.y:12` are all resized equally by
                # that amount.
                tree.resize(p1, "x", -20)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0, y: 20, w: 180, h: 280}
                                - sc.y:6
                                    - p:5 | {x: 180, y: 20, w: 220, h: 140}
                                    - sc.x:8
                                        - sc.y:10
                                            - p:7 | {x: 180, y: 160, w: 110, h: 70}
                                            - p:11 | {x: 180, y: 230, w: 110, h: 70}
                                        - sc.y:12
                                            - p:9 | {x: 290, y: 160, w: 110, h: 70}
                                            - p:13 | {x: 290, y: 230, w: 110, h: 70}
                    """,
                )

        class TestWhenOperationalSiblingIsContainerBeingShrunk:
            @pytest.mark.case_pixel_rounding()
            def test_should_shrink_nested_items_that_are_along_resize_axis_in_proportion_to_their_capacity_to_shrink_along_that_axis(
                self, tree
            ):
                p1 = tree.tab()
                p2 = tree.split(p1, "x")
                p3 = tree.split(p2, "y")
                tree.split(p3, "x")
                tree.split(p3, "x")

                # Shrinking `p:4` should shrink all panes in `sc.y:6`.
                # In `sc.y:6`, those in `sc.x:8` should be shrunk by fractions of 20
                # proportional to their capacity to shrink.
                # Each pane shrinks by: (pane_shrinkability/branch_shrinkability) * resize_amount
                # `p:7` shrinks by: (50 - 10)/170 * 20 ~= 5
                # `p:10` shrinks by: (50 - 10)/170 * 20 ~= 5
                # `p:9` shrinks by: (100 - 10)/170 * 20 ~= 11
                tree.resize(p1, "x", 20)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0, y: 20, w: 220, h: 280}
                                - sc.y:6
                                    - p:5 | {x: 220, y: 20, w: 180, h: 140}
                                    - sc.x:8
                                        - p:7 | {x: 220, y: 160, w: 45, h: 140}
                                        - p:10 | {x: 265, y: 160, w: 45, h: 140}
                                        - p:9 | {x: 310, y: 160, w: 89, h: 140}
                    """,
                )

            def test_should_shrink_nested_items_that_are_against_resize_axis_by_the_same_amount(
                self, tree
            ):
                p1 = tree.tab()
                p2 = tree.split(p1, "x")
                tree.split(p2, "y")

                # Resize `p:4` should shrink all panes in `sc.y:6` by the full resize
                # amount
                tree.resize(p1, "x", 20)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0, y: 20, w: 220, h: 280}
                                - sc.y:6
                                    - p:5 | {x: 220, y: 20, w: 180, h: 140}
                                    - p:7 | {x: 220, y: 160, w: 180, h: 140}
                    """,
                )

            def test_when_all_nested_panes_are_at_min_size_without_any_space_left_to_shrink_it_should_be_a_no_op(
                self, tree
            ):
                p1 = tree.tab()
                p2 = tree.split(p1, "x", 0.9)
                p3 = tree.split(p2, "y")
                p4 = tree.split(p3, "x")
                tree.split(p3, "x")
                tree.split(p4, "x")

                # All of `p:7`, `p:10`, `p:9`, `p:11` are at min size. Since they cannot
                # be shrunk further, they should block the resize of the entire
                # `sc.y:6` operational sibling branch, resulting in a no-op.
                tree.resize(p1, "x", 20)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0, y: 20, w: 360, h: 280}
                                - sc.y:6
                                    - p:5 | {x: 360, y: 20, w: 40, h: 140}
                                    - sc.x:8
                                        - p:7 | {x: 360, y: 160, w: 10, h: 140}
                                        - p:10 | {x: 370, y: 160, w: 10, h: 140}
                                        - p:9 | {x: 380, y: 160, w: 10, h: 140}
                                        - p:11 | {x: 390, y: 160, w: 10, h: 140}
                    """,
                )

            def test_when_nested_panes_cannot_consume_all_of_the_shrink_amount_they_should_consume_as_much_of_the_amount_as_possible(
                self, tree
            ):
                p1 = tree.tab()
                p2 = tree.split(p1, "x", 0.8)
                p3 = tree.split(p2, "y")
                tree.split(p3, "x")

                # `p:7` and `p:9` have 40 width each. They should be able to together
                # consume 30 * 2 = 60 of the requested 100 to shrink and reach min size.
                tree.resize(p1, "x", 100)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0, y: 20, w: 380, h: 280}
                                - sc.y:6
                                    - p:5 | {x: 380, y: 20, w: 20, h: 140}
                                    - sc.x:8
                                        - p:7 | {x: 380, y: 160, w: 10, h: 140}
                                        - p:9 | {x: 390, y: 160, w: 10, h: 140}
                    """,
                )

    class TestResizeInvolvingTabs:
        def test_resizing_panes_under_one_tab_does_not_affect_panes_under_other_tabs(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            tree.split(p2, "y")
            p4 = tree.tab()
            p5 = tree.split(p4, "x")
            tree.split(p5, "y")

            tree.resize(p1, "x", 20)
            tree.resize(p2, "y", 20)

            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - p:4 | {x: 0, y: 20, w: 220, h: 280}
                            - sc.y:6
                                - p:5 | {x: 220, y: 20, w: 180, h: 160}
                                - p:7 | {x: 220, y: 180, w: 180, h: 120}
                    - t:8
                        - sc.x:9
                            - p:10 | {x: 0, y: 20, w: 200, h: 280}
                            - sc.y:12
                                - p:11 | {x: 200, y: 20, w: 200, h: 140}
                                - p:13 | {x: 200, y: 160, w: 200, h: 140}
                """,
            )

        def test_resizing_panes_under_nested_tab_container_does_not_affect_panes_under_other_tabs_in_the_tab_container(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.tab(p1, new_level=True)
            p3 = tree.split(p2, "x")
            p4 = tree.tab(p3, new_level=True)
            p5 = tree.split(p4, "x")

            tree.resize(p5, "x", 20)

            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - tc:5
                                - t:6
                                    - sc.x:7
                                        - p:4 | {x: 0, y: 40, w: 400, h: 260}
                                - t:8
                                    - sc.x:9
                                        - p:10 | {x: 0, y: 40, w: 200, h: 260}
                                        - tc:12
                                            - t:13
                                                - sc.x:14
                                                    - p:11 | {x: 200, y: 60, w: 200, h: 240}
                                            - t:15
                                                - sc.x:16
                                                    - p:17 | {x: 200, y: 60, w: 120, h: 240}
                                                    - p:18 | {x: 320, y: 60, w: 80, h: 240}
                """,
            )

        def test_when_operational_sibling_is_tab_container_all_its_panes_under_all_tabs_against_resize_axis_get_resized_by_full_amount(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.tab(p2, new_level=True)
            p4 = tree.split(p3, "y")
            tree.split(p4, "y")

            tree.resize(p1, "x", 20)

            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - p:4 | {x: 0, y: 20, w: 220, h: 280}
                            - tc:6
                                - t:7
                                    - sc.x:8
                                        - p:5 | {x: 220, y: 40, w: 180, h: 260}
                                - t:9
                                    - sc.y:10
                                        - p:11 | {x: 220, y: 40, w: 180, h: 130}
                                        - p:12 | {x: 220, y: 170, w: 180, h: 65}
                                        - p:13 | {x: 220, y: 235, w: 180, h: 65}
                """,
            )

        def test_resizing_lone_pane_under_nested_tab_should_resize_entire_tab_container(
            self, tree
        ):
            p1 = tree.tab()
            tree.split(p1, "x")
            p3 = tree.tab(p1, new_level=True)

            # Splits under first sub-tab. Second tab has lone pane p3.
            p4 = tree.split(p1, "x")
            tree.split(p4, "y")

            tree.resize(p3, "x", 20)

            # Resizing `p:11` should have affected panes in the first sub tab as well as
            # the entire TabContainer gets resized.
            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - tc:6
                                - t:7
                                    - sc.x:8
                                        - p:4 | {x: 0, y: 40, w: 110, h: 260}
                                        - sc.y:13
                                            - p:12 | {x: 110, y: 40, w: 110, h: 130}
                                            - p:14 | {x: 110, y: 170, w: 110, h: 130}
                                - t:9
                                    - sc.x:10
                                        - p:11 | {x: 0, y: 40, w: 220, h: 260}
                            - p:5 | {x: 220, y: 20, w: 180, h: 280}
                """,
            )

        def test_when_a_sole_pane_under_a_nested_tc_is_resized_then_it_gets_resized_as_if_it_were_a_pane_directly_under_container_of_said_tc(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")
            p4 = tree.tab(p3, new_level=True)

            tree.resize(p4, "y", -20)

            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - p:4 | {x: 0, y: 20, w: 200, h: 280}
                            - sc.y:6
                                - p:5 | {x: 200, y: 20, w: 200, h: 120}
                                - tc:8
                                    - t:9
                                        - sc.x:10
                                            - p:7 | {x: 200, y: 160, w: 200, h: 140}
                                    - t:11
                                        - sc.x:12
                                            - p:13 | {x: 200, y: 160, w: 200, h: 140}
                """,
            )

        def test_resizing_top_level_pane_with_siblings_under_nested_tab_along_axis_should_only_affect_the_pane_and_its_sibling(
            self, tree
        ):
            p1 = tree.tab()
            tree.split(p1, "x")
            p3 = tree.tab(p1, new_level=True)
            p4 = tree.split(p3, "x")

            tree.resize(p4, "x", 20)

            # Resizing p4 should only affect itself and p3.
            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - tc:6
                                - t:7
                                    - sc.x:8
                                        - p:4 | {x: 0, y: 40, w: 200, h: 260}
                                - t:9
                                    - sc.x:10
                                        - p:11 | {x: 0, y: 40, w: 120, h: 260}
                                        - p:12 | {x: 120, y: 40, w: 80, h: 260}
                            - p:5 | {x: 200, y: 20, w: 200, h: 280}
                """,
            )

        def test_resizing_top_level_pane_with_siblings_under_nested_tab_against_axis_should_affect_the_entire_tab_container_and_the_tab_containers_sibling(
            self, tree
        ):
            p1 = tree.tab()
            tree.split(p1, "x")
            p3 = tree.tab(p1, new_level=True)
            p4 = tree.split(p3, "y")

            tree.resize(p4, "x", 20)

            # p4 is in the y-direction. Resizing it along the x-direction will affect
            # everything in the containing SplitContainer as well as the containing
            # TabContainer.
            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - tc:6
                                - t:7
                                    - sc.x:8
                                        - p:4 | {x: 0, y: 40, w: 220, h: 260}
                                - t:9
                                    - sc.y:10
                                        - p:11 | {x: 0, y: 40, w: 220, h: 130}
                                        - p:12 | {x: 0, y: 170, w: 220, h: 130}
                            - p:5 | {x: 220, y: 20, w: 180, h: 280}
                """,
            )

        def test_when_tab_container_is_resized_on_y_axis_then_the_tab_bar_height_is_also_considered(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")
            tree.tab(p3, new_level=True)

            tree.resize(p2, "y", -20)

            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - p:4 | {x: 0, y: 20, w: 200, h: 280}
                            - sc.y:6
                                - p:5 | {x: 200, y: 20, w: 200, h: 120}
                                - tc:8
                                    - t:9
                                        - sc.x:10
                                            - p:7 | {x: 200, y: 160, w: 200, h: 140}
                                    - t:11
                                        - sc.x:12
                                            - p:13 | {x: 200, y: 160, w: 200, h: 140}
                """,
            )


class TestRemove:
    def test_when_all_panes_are_removed_then_tree_is_empty(self, tree):
        p1 = tree.tab()
        p2 = tree.tab(p1)
        p3 = tree.split(p2, "x")
        p4 = tree.split(p3, "y")

        tree.remove(p1)
        tree.remove(p2)
        tree.remove(p3)
        tree.remove(p4)

        assert tree.is_empty

    def test_when_operational_sibling_is_pane_then_it_is_returned_as_next_focus_node(
        self, tree
    ):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")

        p = tree.remove(p1)

        assert p is p2

    def test_when_operational_sibling_is_sc_then_its_mru_pane_is_returned_as_next_focus_node(
        self, tree
    ):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")
        p3 = tree.split(p2, "y")
        tree.split(p3, "y")

        tree.focus(p3)

        p = tree.remove(p1)

        assert p is p3

    def test_when_operational_sibling_is_tc_then_its_mru_pane_is_returned_as_next_focus_node(
        self, tree
    ):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")
        p3 = tree.tab(p2, new_level=True)
        p4 = tree.split(p2, "y")

        tree.focus(p4)

        p = tree.remove(p3)

        assert p is p4

    def test_when_tree_becomes_empty_then_returns_none_as_nothing_left_for_subsequent_focus(
        self, tree
    ):
        p1 = tree.tab()
        p = tree.remove(p1)

        assert p is None

    def test_when_any_pane_except_last_pane_in_container_is_removed_then_right_sibling_consumes_space(
        self, tree
    ):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")
        tree.split(p2, "x")

        tree.remove(p2)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 200, h: 280}
                        - p:6 | {x: 200, y: 20, w: 200, h: 280}
            """,
        )

    def test_when_last_pane_in_container_is_removed_then_left_sibling_consumes_space(
        self, tree
    ):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")
        p3 = tree.split(p2, "x")

        tree.remove(p3)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 200, h: 280}
                        - p:5 | {x: 200, y: 20, w: 200, h: 280}
            """,
        )

    def test_when_sibling_that_consumes_space_has_nested_items_then_they_are_grown_in_proportion_to_their_respective_sizes(
        self, tree
    ):
        p1 = tree.tab()
        p2 = tree.split(p1, "x", 0.2)
        p3 = tree.split(p2, "x")
        p4 = tree.split(p3, "y")
        p5 = tree.split(p4, "x")
        tree.split(p5, "x")

        tree.remove(p2)

        assert tree_matches_repr(
            tree,
            """
                - tc:1
                    - t:2
                        - sc.x:3
                            - p:4 | {x: 0, y: 20, w: 80, h: 280}
                            - sc.y:7
                                - p:6 | {x: 80, y: 20, w: 320, h: 140}
                                - sc.x:9
                                    - p:8 | {x: 80, y: 160, w: 160, h: 140}
                                    - p:10 | {x: 240, y: 160, w: 80, h: 140}
                                    - p:11 | {x: 320, y: 160, w: 80, h: 140}
                """,
        )

    def test_removal_in_nested_container(self, make_tree_with_subscriber):
        tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)

        p1 = tree.tab()
        p2 = tree.split(p1, "x")
        p3 = tree.split(p2, "y")
        tree.split(p3, "y")

        tree.remove(p3)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 200, h: 280}
                        - sc.y:6
                            - p:5 | {x: 200, y: 20, w: 200, h: 140}
                            - p:8 | {x: 200, y: 160, w: 200, h: 140}
            """,
        )

        assert callback.mock_calls == [mock.call([p3])]

    def test_when_last_pane_under_tab_is_removed_then_the_tab_is_removed(
        self, make_tree_with_subscriber
    ):
        tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)

        p1 = tree.tab()
        sc1, t1, _ = p1.get_ancestors()
        tree.tab()

        tree.remove(p1)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:5
                    - sc.x:6
                        - p:7 | {x: 0, y: 20, w: 400, h: 280}
            """,
        )

        assert callback.mock_calls == [
            mock.call([p1, sc1, t1]),
        ]

    def test_when_last_pane_under_last_tab_of_tab_container_is_removed_then_then_tab_container_is_removed(
        self, make_tree_with_subscriber
    ):
        tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)

        p1 = tree.tab()
        p2 = tree.split(p1, "x")
        p3 = tree.tab(p2, new_level=True)

        sc1, t1, tc, _, _, _ = p2.get_ancestors()
        sc2, t2, tc, _, _, _ = p3.get_ancestors()

        tree.remove(p2)
        tree.remove(p3)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0, y: 20, w: 400, h: 280}
            """,
        )

        assert callback.mock_calls == [
            mock.call([p2, sc1, t1]),
            mock.call([p3, sc2, t2, tc]),
        ]

    def test_tab_removal_works_in_nested_tabs(self, tree):
        p1 = tree.tab()
        p2 = tree.tab(p1, new_level=True)
        tree.tab(p2)

        tree.remove(p2)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:5
                            - t:6
                                - sc.x:7
                                    - p:4 | {x: 0, y: 40, w: 400, h: 260}
                            - t:11
                                - sc.x:12
                                    - p:13 | {x: 0, y: 40, w: 400, h: 260}
            """,
        )

    def test_when_penultimate_tab_is_removed_from_nested_tab_level_then_the_nested_tab_level_is_maintained_without_the_last_tab_being_merged_upwards(
        self, tree
    ):
        p1 = tree.tab()
        p2 = tree.tab(p1, new_level=True)

        tree.remove(p2)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:5
                            - t:6
                                - sc.x:7
                                    - p:4 | {x: 0, y: 40, w: 400, h: 260}
            """,
        )

    def test_subscribers_are_notified_of_removed_nodes_in_the_order_they_are_removed(
        self, make_tree_with_subscriber
    ):
        tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)

        p1 = tree.tab()
        sc, t, tc = p1.get_ancestors()
        p2 = tree.split(p1, "x")
        p3 = tree.split(p2, "x")

        tree.remove(p1)
        tree.remove(p2)
        tree.remove(p3)

        assert callback.mock_calls == [
            mock.call([p1]),
            mock.call([p2]),
            mock.call([p3, sc, t, tc]),
        ]

    class TestPruning:
        class TestPositiveCases:
            def test_when_n1_n2_n3_chain_is_sc_sc_p_then_n1_and_n3_are_linked(
                self, make_tree_with_subscriber
            ):
                tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)
                p1 = tree.tab()
                p2 = tree.split(p1, "x")
                p3 = tree.split(p2, "y")
                sc = p3.parent

                tree.remove(p3)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0, y: 20, w: 200, h: 280}
                                - p:5 | {x: 200, y: 20, w: 200, h: 280}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p3, sc]),
                ]

            def test_when_n1_n2_n3_chain_is_t_sc_sc_then_n1_and_n3_are_linked(
                self, make_tree_with_subscriber
            ):
                tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)
                p1 = tree.tab()
                sc = p1.parent
                p2 = tree.split(p1, "x")
                tree.split(p2, "y")

                tree.remove(p1)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.y:6
                                - p:5 | {x: 0, y: 20, w: 400, h: 140}
                                - p:7 | {x: 0, y: 160, w: 400, h: 140}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p1, sc]),
                ]

            def test_when_n1_n2_n3_chain_is_sc_sc_sc_then_n1_absorbs_children_of_n3(
                self, make_tree_with_subscriber
            ):
                tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)
                p1 = tree.tab()
                p2 = tree.split(p1, "x")
                p3 = tree.split(p2, "y")
                tree.split(p3, "x")
                sc_x, sc_y, _, _, _ = p3.get_ancestors()

                tree.remove(p2)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0, y: 20, w: 200, h: 280}
                                - p:7 | {x: 200, y: 20, w: 100, h: 280}
                                - p:9 | {x: 300, y: 20, w: 100, h: 280}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p2, sc_x, sc_y]),
                ]

            def test_when_n1_n2_n3_chain_is_sc_sc_tc_then_n1_and_n3_are_linked(
                self, make_tree_with_subscriber
            ):
                tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)
                p1 = tree.tab()
                p2 = tree.split(p1, "x")
                p3 = tree.split(p2, "y")
                tree.tab(p3, new_level=True)

                tree.remove(p2)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0, y: 20, w: 200, h: 280}
                                - tc:8
                                    - t:9
                                        - sc.x:10
                                            - p:7 | {x: 200, y: 40, w: 200, h: 260}
                                    - t:11
                                        - sc.x:12
                                            - p:13 | {x: 200, y: 40, w: 200, h: 260}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p2, p2.parent]),
                ]

        class TestNegativeCases:
            def test_when_n1_n2_n3_chain_is_t_sc_p_then_no_pruning_happens(
                self, make_tree_with_subscriber
            ):
                tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)
                p1 = tree.tab()
                p2 = tree.split(p1, "x")

                tree.remove(p2)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0, y: 20, w: 400, h: 280}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p2]),
                ]

            def test_when_n1_n2_n3_chain_is_sc_tc_t_then_no_pruning_happens(
                self, make_tree_with_subscriber
            ):
                tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)
                p1 = tree.tab()
                p2 = tree.split(p1, "x")
                p3 = tree.tab(p2, new_level=True)
                sc, t, _, _, _, _ = p3.get_ancestors()

                tree.remove(p3)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0, y: 20, w: 200, h: 280}
                                - tc:6
                                    - t:7
                                        - sc.x:8
                                            - p:5 | {x: 200, y: 40, w: 200, h: 260}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p3, sc, t]),
                ]

            def test_when_n1_n2_n3_chain_is_none_tc_t_then_no_pruning_happens(
                self, make_tree_with_subscriber
            ):
                tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)
                tree.tab()
                p2 = tree.tab()
                sc, t, _ = p2.get_ancestors()

                tree.remove(p2)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0, y: 20, w: 400, h: 280}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p2, sc, t]),
                ]

            def test_when_n1_n2_n3_chain_is_t_sc_tc_then_no_pruning_happens(
                self, make_tree_with_subscriber
            ):
                tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)
                p1 = tree.tab()
                p2 = tree.split(p1, "x")
                tree.tab(p2, new_level=True)

                tree.remove(p1)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - tc:6
                                    - t:7
                                        - sc.x:8
                                            - p:5 | {x: 0, y: 40, w: 400, h: 260}
                                    - t:9
                                        - sc.x:10
                                            - p:11 | {x: 0, y: 40, w: 400, h: 260}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p1]),
                ]


class TestFocus:
    def test_activates_tab_chain_of_focused_pane(self, tree):
        p1 = tree.tab()
        p2 = tree.tab(p1)
        p3 = tree.split(p2, "x")
        p4 = tree.tab(p3, new_level=True)
        p5 = tree.split(p4, "x")

        tree.focus(p5)

        tc2, tc1 = p5.get_ancestors(TabContainer)
        t2, t1 = p5.get_ancestors(Tab)

        assert tc2.active_child is t2
        assert tc1.active_child is t1

    def test_deactivates_tab_chain_of_unfocused_pane(self, tree):
        p1 = tree.tab()
        p2 = tree.split(p1, "x")
        p3 = tree.tab(p2, new_level=True)
        tree.focus(p3)

        p4 = tree.tab(p1)
        p5 = tree.split(p4, "x")
        p6 = tree.tab(p5, new_level=True)

        tree.focus(p6)

        tc2, tc1 = p3.get_ancestors(TabContainer)
        t2, t1 = p3.get_ancestors(Tab)

        assert tc2.active_child is t2
        assert tc1.active_child is not t1


class TestMotions:
    class TestRight:
        def test_motion_along_axis(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "x")

            assert tree.right(p2) is p3

        def test_motion_along_axis_in_nested_level(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")
            p4 = tree.split(p3, "x")

            assert tree.right(p3) is p4

        def test_motion_against_axis(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p1, "y")

            assert tree.right(p3, wrap=False) is p2

        def test_motion_against_axis_in_nested_level(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")
            p4 = tree.split(p3, "x")
            p5 = tree.split(p3, "y")

            assert tree.right(p5) is p4

        def test_when_wrap_is_true_and_pane_is_at_edge_of_screen_then_pane_from_other_edge_of_screen_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "x")

            assert tree.right(p3, wrap=True) is p1

        def test_when_wrap_is_true_and_pane_is_its_own_sibling_then_the_pane_itself_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            tree.split(p2, "x")

            assert tree.right(p1, wrap=True) is p1

        def test_when_wrap_is_false_and_pane_is_at_edge_of_screen_then_the_pane_itself_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "x")

            assert tree.right(p3, wrap=False) is p3

        def test_when_there_are_multiple_adjacent_panes_then_the_most_recently_focused_one_is_chosen(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")
            p4 = tree.split(p3, "y")
            p5 = tree.split(p4, "y")
            tree.focus(p5)
            tree.focus(p3)
            tree.focus(p4)

            assert tree.right(p1) is p4

        def test_non_adjacent_panes_further_away_in_the_requested_direction_are_not_considered(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x", 0.1)
            p3 = tree.split(p1, "x")

            tree.focus(p3)
            assert tree.right(p1) is p3
            tree.focus(p2)
            assert tree.right(p1) is p3

        def test_adjacent_panes_that_only_partly_share_borders_are_candidates(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")

            tree.split(p1, "y", 0.6)
            p4 = tree.split(p1, "y", 0.5)

            tree.split(p2, "y", 0.8)
            p6 = tree.split(p2, "y", 0.5)

            # p2 and p6 both touch p4. p6 is further down and does not touch p4.

            tree.focus(p2)
            assert tree.right(p4) is p2
            tree.focus(p6)
            assert tree.right(p4) is p6

        def test_when_there_are_panes_along_the_same_border_but_not_adjacent_then_they_are_not_considered(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")

            p3 = tree.split(p1, "y", 0.4)
            tree.split(p3, "y", 0.5)

            p5 = tree.split(p2, "y", 0.2)
            p6 = tree.split(p5, "y", 0.8)

            tree.focus(p6)
            tree.focus(p2)

            # The only adjacent neighbor of p3 is p5. p2 and p6 are along p3's border
            # but not adjacent.
            assert tree.right(p3) is p5

        def test_when_adjacent_pane_is_under_tab_container_then_only_the_visible_pane_is_considered(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.tab(p2, new_level=True)
            p4 = tree.tab(p3)
            tree.focus(p4)

            assert tree.right(p1) is p4

        def test_deeply_nested_adjacent_panes_under_different_super_nodes(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p1, "y")
            p4 = tree.split(p2, "y")

            pa1 = p3
            pa2 = tree.split(pa1, "x")
            pa3 = tree.split(pa2, "y")
            pa4 = tree.split(pa3, "x")
            tree.split(pa4, "y")

            pb1 = p4
            tree.split(pb1, "x")
            pb3 = tree.split(pb1, "y", 0.2)
            pb4 = tree.split(pb3, "y")
            tree.split(pb3, "x")

            tree.focus(pb4)

            assert tree.right(pa4) is pb4

    class TestLeft:
        def test_motion_along_axis(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            tree.split(p2, "x")

            assert tree.left(p2) is p1

        def test_motion_along_axis_in_nested_level(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")
            p4 = tree.split(p3, "x")

            assert tree.left(p4) is p3

        def test_motion_against_axis(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")

            assert tree.left(p3, wrap=False) is p1

        def test_motion_against_axis_in_nested_level(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")
            p4 = tree.split(p3, "x")
            p5 = tree.split(p4, "y")

            assert tree.left(p5) is p3

        def test_when_wrap_is_true_and_pane_is_at_edge_of_screen_then_pane_from_other_edge_of_screen_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "x")

            assert tree.left(p1, wrap=True) is p3

        def test_when_wrap_is_true_and_pane_is_its_own_sibling_then_the_pane_itself_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            tree.split(p2, "x")

            assert tree.left(p1, wrap=True) is p1

        def test_when_wrap_is_false_and_pane_is_at_edge_of_screen_then_the_pane_itself_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            tree.split(p2, "x")

            assert tree.left(p1, wrap=False) is p1

        def test_when_there_are_multiple_adjacent_panes_then_the_most_recently_focused_one_is_chosen(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p1, "y")
            p4 = tree.split(p3, "y")
            p5 = tree.split(p4, "y")
            tree.focus(p5)
            tree.focus(p3)
            tree.focus(p4)

            assert tree.left(p2) is p4

        def test_non_adjacent_panes_further_away_in_the_requested_direction_are_not_considered(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x", 0.9)
            p3 = tree.split(p2, "x")

            tree.focus(p2)
            assert tree.left(p3) is p2
            tree.focus(p1)
            assert tree.left(p3) is p2

        def test_adjacent_panes_that_only_partly_share_borders_are_candidates(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")

            p3 = tree.split(p1, "y", 0.6)
            p4 = tree.split(p1, "y", 0.5)

            tree.split(p2, "y", 0.8)
            p6 = tree.split(p2, "y", 0.5)

            # p3 and p4 both touch p6. p1 is further up and does not touch p6.

            tree.focus(p3)
            assert tree.left(p6) is p3
            tree.focus(p4)
            assert tree.left(p6) is p4

        def test_when_there_are_panes_along_the_same_border_but_not_adjacent_then_they_are_not_considered(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")

            p3 = tree.split(p1, "y", 0.2)
            tree.split(p3, "y", 0.8)

            p5 = tree.split(p2, "y", 0.4)
            p6 = tree.split(p5, "y", 0.5)

            tree.focus(p6)
            tree.focus(p2)

            # The only adjacent neighbor of p5 is p3. p1 and p4 are along p5's border
            # but not adjacent.
            assert tree.left(p5) is p3

        def test_when_adjacent_pane_is_under_tab_container_then_only_the_visible_pane_is_considered(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.tab(p1, new_level=True)
            p4 = tree.tab(p3)
            tree.focus(p4)

            assert tree.left(p2) is p4

        def test_deeply_nested_adjacent_panes_in_different_super_containers(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p1, "y")
            p4 = tree.split(p2, "y")

            pa1 = p3
            pa2 = tree.split(pa1, "x")
            pa3 = tree.split(pa2, "y")
            pa4 = tree.split(pa3, "x")
            tree.split(pa4, "y")

            pb1 = p4
            tree.split(pb1, "x")
            pb3 = tree.split(pb1, "y", 0.2)
            pb4 = tree.split(pb3, "y")
            tree.split(pb3, "x")

            tree.focus(pa4)

            assert tree.left(pb4) is pa4

    class TestDown:
        def test_motion_along_axis(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "y")

            assert tree.down(p2) is p3

        def test_motion_along_axis_in_nested_level(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "x")
            p4 = tree.split(p3, "y")

            assert tree.down(p3) is p4

        def test_motion_against_axis(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p1, "x")

            assert tree.down(p3, wrap=False) is p2

        def test_motion_against_axis_in_nested_level(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "x")
            p4 = tree.split(p3, "y")
            p5 = tree.split(p3, "x")

            assert tree.down(p5) is p4

        def test_when_wrap_is_true_and_pane_is_at_edge_of_screen_then_pane_from_other_edge_of_screen_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "y")

            assert tree.down(p3, wrap=True) is p1

        def test_when_wrap_is_true_and_pane_is_its_own_sibling_then_the_pane_itself_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            tree.split(p2, "y")

            assert tree.down(p1, wrap=True) is p1

        def test_when_wrap_is_false_and_pane_is_at_edge_of_screen_then_the_pane_itself_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "y")

            assert tree.down(p3, wrap=False) is p3

        def test_when_there_are_multiple_adjacent_panes_then_the_most_recently_focused_one_is_chosen(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "x")
            p4 = tree.split(p3, "x")
            p5 = tree.split(p4, "x")
            tree.focus(p5)
            tree.focus(p3)
            tree.focus(p4)

            assert tree.down(p1) is p4

        def test_non_adjacent_panes_further_away_in_the_requested_direction_are_not_considered(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y", 0.1)
            p3 = tree.split(p1, "y")

            tree.focus(p3)
            assert tree.down(p1) is p3
            tree.focus(p2)
            assert tree.down(p1) is p3

        def test_adjacent_panes_that_only_partly_share_borders_are_candidates(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")

            tree.split(p1, "x", 0.6)
            p4 = tree.split(p1, "x", 0.5)

            tree.split(p2, "x", 0.8)
            p6 = tree.split(p2, "x", 0.5)

            # p2 and p6 both touch p4. p6 does not touch p4.

            tree.focus(p2)
            assert tree.down(p4) is p2
            tree.focus(p6)
            assert tree.down(p4) is p6

        def test_when_there_are_panes_along_the_same_border_but_not_adjacent_then_they_are_not_considered(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")

            p3 = tree.split(p1, "x", 0.4)
            tree.split(p3, "x", 0.5)

            p5 = tree.split(p2, "x", 0.2)
            p6 = tree.split(p5, "x", 0.8)

            tree.focus(p6)
            tree.focus(p2)

            # The only adjacent neighbor of p3 is p5. p2 and p6 are along p3's border
            # but not adjacent.
            assert tree.down(p3) is p5

        def test_when_adjacent_pane_is_under_tab_container_then_only_the_visible_pane_is_considered(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.tab(p2, new_level=True)
            p4 = tree.tab(p3)
            tree.focus(p4)

            assert tree.down(p1) is p4

        def test_deeply_nested_adjacent_panes_in_different_super_containers(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p1, "x")
            p4 = tree.split(p2, "x")

            pa1 = p3
            pa2 = tree.split(pa1, "y")
            pa3 = tree.split(pa2, "x")
            pa4 = tree.split(pa3, "y")
            tree.split(pa4, "x")

            pb1 = p4
            tree.split(pb1, "y")
            pb3 = tree.split(pb1, "x", 0.2)
            pb4 = tree.split(pb3, "x")
            tree.split(pb3, "y")

            tree.focus(pb4)

            assert tree.down(pa4) is pb4

        def test_when_there_are_tab_bars_between_panes_then_they_are_ignored_for_adjacency_calculations(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            tree.split(p2, "x")

            p4 = tree.tab(p2, new_level=True)
            p5 = tree.tab(p4, new_level=True)
            p6 = tree.tab(p5, new_level=True)

            tree.focus(p6)

            # p6 is still the most relevant adjacent pane downwards from p1, despite it
            # being 'further' away vertically than p3, due to the many tab bars in
            # between.
            assert tree.down(p1) is p6

    class TestUp:
        def test_motion_along_axis(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            tree.split(p2, "y")

            assert tree.up(p2) is p1

        def test_motion_along_axis_in_nested_level(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "x")
            p4 = tree.split(p3, "y")

            assert tree.up(p4) is p3

        def test_motion_against_axis(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "x")

            assert tree.up(p3, wrap=False) is p1

        def test_motion_against_axis_in_nested_level(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "x")
            p4 = tree.split(p3, "y")
            p5 = tree.split(p4, "x")

            assert tree.up(p5) is p3

        def test_when_wrap_is_true_and_pane_is_at_edge_of_screen_then_pane_from_other_edge_of_screen_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "y")

            assert tree.up(p1, wrap=True) is p3

        def test_when_wrap_is_true_and_pane_is_its_own_sibling_then_the_pane_itself_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            tree.split(p2, "y")

            assert tree.up(p1, wrap=True) is p1

        def test_when_wrap_is_false_and_pane_is_at_edge_of_screen_then_the_pane_itself_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            tree.split(p2, "y")

            assert tree.up(p1, wrap=False) is p1

        def test_when_there_are_multiple_adjacent_panes_then_the_most_recently_focused_one_is_chosen(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p1, "x")
            p4 = tree.split(p3, "x")
            p5 = tree.split(p4, "x")
            tree.focus(p5)
            tree.focus(p3)
            tree.focus(p4)

            assert tree.up(p2) is p4

        def test_non_adjacent_panes_further_away_in_the_requested_direction_are_not_considered(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y", 0.9)
            p3 = tree.split(p2, "y")

            tree.focus(p2)
            assert tree.up(p3) is p2
            tree.focus(p1)
            assert tree.up(p3) is p2

        def test_adjacent_panes_that_only_partly_share_borders_are_candidates(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")

            p3 = tree.split(p1, "x", 0.6)
            p4 = tree.split(p1, "x", 0.5)

            tree.split(p2, "x", 0.8)
            p6 = tree.split(p2, "x", 0.5)

            # p3 and p4 both touch p6. p1 does not touch p6.

            tree.focus(p3)
            assert tree.up(p6) is p3
            tree.focus(p4)
            assert tree.up(p6) is p4

        def test_when_there_are_panes_along_the_same_border_but_not_adjacent_then_they_are_not_considered(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")

            p3 = tree.split(p1, "x", 0.2)
            tree.split(p3, "x", 0.8)

            p5 = tree.split(p2, "x", 0.4)
            p6 = tree.split(p5, "x", 0.5)

            tree.focus(p6)
            tree.focus(p2)

            # The only adjacent neighbor of p5 is p3. p1 and p4 are along p5's border
            # but not adjacent.
            assert tree.up(p5) is p3

        def test_when_adjacent_pane_is_under_tab_container_then_only_the_visible_pane_is_considered(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.tab(p1, new_level=True)
            p4 = tree.tab(p3)
            tree.focus(p4)

            assert tree.up(p2) is p4

        def test_deeply_nested_adjacent_panes_in_different_super_containers(self, tree):
            p1 = tree.tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p1, "x")
            p4 = tree.split(p2, "x")

            pa1 = p3
            pa2 = tree.split(pa1, "y")
            pa3 = tree.split(pa2, "x")
            pa4 = tree.split(pa3, "y")
            tree.split(pa4, "x")

            pb1 = p4
            tree.split(pb1, "y")
            pb3 = tree.split(pb1, "x", 0.2)
            pb4 = tree.split(pb3, "x")
            tree.split(pb3, "y")

            tree.focus(pa4)

            assert tree.up(pb4) is pa4


class TestTabMotions:
    class TestNext:
        def test_when_any_node_is_provided_then_mru_pane_in_next_tab_of_nearest_tc_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.tab(p1)
            p3 = tree.split(p2, "x")
            tree.focus(p3)
            tree.focus(p1)

            sc, t, _ = p1.get_ancestors()

            p = tree.next_tab(p1)
            assert p is p3

            p = tree.next_tab(sc)
            assert p is p3

            p = tree.next_tab(t)
            assert p is p3

            tree.focus(p2)
            p = tree.next_tab(t)
            assert p is p2

        def test_when_any_node_under_nested_tc_is_provided_then_mru_pane_in_next_tab_of_nearest_tc_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.tab(p2, new_level=True)
            p4 = tree.split(p3, "y")
            tree.focus(p4)

            p = tree.next_tab(p2)

            assert p is p4

        def test_when_a_node_is_provided_that_is_not_under_a_tc_then_an_error_is_raised(
            self, tree
        ):
            p1 = tree.tab()
            tree.tab()

            _, _, tc = p1.get_ancestors()

            err_msg = "The provided node is not under a `TabContainer` node"
            with pytest.raises(ValueError, match=err_msg):
                tree.next_tab(tc)

        def test_wrap_is_respected(self, tree):
            p1 = tree.tab()
            p2 = tree.tab(p1)

            p = tree.next_tab(p2, wrap=True)
            assert p is p1

            p = tree.next_tab(p2, wrap=False)
            assert p is None

    class TestPrev:
        def test_when_any_node_is_provided_then_mru_pane_in_prev_tab_of_nearest_tc_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.tab(p1)
            tree.focus(p2)
            tree.focus(p3)

            sc, t, _ = p3.get_ancestors()

            p = tree.prev_tab(p3)
            assert p is p2

            p = tree.prev_tab(sc)
            assert p is p2

            p = tree.prev_tab(t)
            assert p is p2

            tree.focus(p1)
            p = tree.prev_tab(t)
            assert p is p1

        def test_when_any_node_under_nested_tc_is_provided_then_mru_pane_in_prev_tab_of_nearest_tc_is_returned(
            self, tree
        ):
            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.tab(p2, new_level=True)
            p4 = tree.split(p2, "y")
            tree.focus(p4)

            p = tree.prev_tab(p3)

            assert p is p4

        def test_when_a_node_is_provided_that_is_not_under_a_tc_then_an_error_is_raised(
            self, tree
        ):
            p1 = tree.tab()
            tree.tab()

            _, _, tc = p1.get_ancestors()

            err_msg = "The provided node is not under a `TabContainer` node"
            with pytest.raises(ValueError, match=err_msg):
                tree.prev_tab(tc)

        def test_wrap_is_respected(self, tree):
            p1 = tree.tab()
            p2 = tree.tab(p1)

            p = tree.prev_tab(p1, wrap=True)
            assert p is p2

            p = tree.prev_tab(p1, wrap=False)
            assert p is None


class TestConfig:
    def test_fall_back_to_default(self, tree: Tree):
        tree.set_config("window.margin", 10)

        assert (
            tree.get_config("window.margin", for_level=1, fall_back_to_default=True)
            == 10
        )
        assert (
            tree.get_config("window.margin", for_level=3, fall_back_to_default=True)
            == 10
        )

        with pytest.raises(KeyError):
            tree.get_config("window.margin", for_level=3, fall_back_to_default=False)
        with pytest.raises(KeyError):
            tree.get_config("window.margin", for_level=1, fall_back_to_default=False)

    class TestWindowConfig:
        def test_margin(self, tree: Tree):
            tree.set_config("window.margin", 10, for_level=1)
            tree.set_config("window.margin", 11, for_level=2)
            tree.set_config("window.margin", 12, for_level=3)

            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.tab(p2, new_level=True)

            assert p1.box.margin == 10
            assert p2.box.margin == 11
            assert p3.box.margin == 11

        def test_border_size(self, tree: Tree):
            tree.set_config("window.border_size", 10, for_level=1)
            tree.set_config("window.border_size", 11, for_level=2)
            tree.set_config("window.border_size", 12, for_level=3)

            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.tab(p2, new_level=True)

            assert p1.box.border == 10
            assert p2.box.border == 11
            assert p3.box.border == 11

        def test_padding(self, tree: Tree):
            tree.set_config("window.padding", 10, for_level=1)
            tree.set_config("window.padding", 11, for_level=2)
            tree.set_config("window.padding", 12, for_level=3)

            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.tab(p2, new_level=True)

            assert p1.box.padding == 10
            assert p2.box.padding == 11
            assert p3.box.padding == 11

    class TestTabBarConfig:
        def test_height(self, tree: Tree):
            tree.set_config("tab_bar.height", 20, for_level=1)
            tree.set_config("tab_bar.height", 10, for_level=2)
            tree.set_config("tab_bar.height", 5, for_level=3)

            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.tab(p2, new_level=True)

            tc1, *_ = p1.get_ancestors(of_type=TabContainer)
            tc2, *_ = p3.get_ancestors(of_type=TabContainer)

            assert tc1.tab_bar.box.principal_rect.h == 20
            assert tc2.tab_bar.box.principal_rect.h == 10

        def test_margin(self, tree: Tree):
            tree.set_config("tab_bar.margin", 10, for_level=1)
            tree.set_config("tab_bar.margin", 11, for_level=2)
            tree.set_config("tab_bar.margin", 12, for_level=3)

            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.tab(p2, new_level=True)

            tc1, *_ = p1.get_ancestors(of_type=TabContainer)
            tc2, *_ = p3.get_ancestors(of_type=TabContainer)

            assert tc1.tab_bar.box.margin == 10
            assert tc2.tab_bar.box.margin == 11

        def test_border_size(self, tree: Tree):
            tree.set_config("tab_bar.border_size", 10, for_level=1)
            tree.set_config("tab_bar.border_size", 11, for_level=2)
            tree.set_config("tab_bar.border_size", 12, for_level=3)

            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.tab(p2, new_level=True)

            tc1, *_ = p1.get_ancestors(of_type=TabContainer)
            tc2, *_ = p3.get_ancestors(of_type=TabContainer)

            assert tc1.tab_bar.box.border == 10
            assert tc2.tab_bar.box.border == 11

        def test_padding(self, tree: Tree):
            tree.set_config("tab_bar.padding", 10, for_level=1)
            tree.set_config("tab_bar.padding", 11, for_level=2)
            tree.set_config("tab_bar.padding", 12, for_level=3)

            p1 = tree.tab()
            p2 = tree.split(p1, "x")
            p3 = tree.tab(p2, new_level=True)

            tc1, *_ = p1.get_ancestors(of_type=TabContainer)
            tc2, *_ = p3.get_ancestors(of_type=TabContainer)

            assert tc1.tab_bar.box.padding == 10
            assert tc2.tab_bar.box.padding == 11


class TestIterWalk:
    def test_new_tree_instance_has_no_nodes(self, tree):
        assert list(tree.iter_walk()) == []


class TestSubscribe:
    def test_returns_subscription_id(self, tree):
        callback = mock.Mock()

        subscription_id = tree.subscribe(TreeEvent.node_added, callback)

        assert isinstance(subscription_id, str)


class TestRepr:
    def test_empty_tree(self, tree):
        assert repr(tree) == "<empty>"
