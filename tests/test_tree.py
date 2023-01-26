# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from unittest import mock

import pytest
from qtile_bonsai.tree import (
    Node,
    Pane,
    Tab,
    TabBar,
    TabContainer,
    Tree,
    TreeEvent,
    UnitRect,
    tree_matches_repr,
)


@pytest.fixture(autouse=True)
def reset_node_id_seq():
    Node.reset_id_seq()
    Pane.min_size = 0.05
    TabBar.default_height = 0.02


@pytest.fixture()
def make_tree_with_subscriber():
    def _make_tree_with_subscriber(event: TreeEvent):
        tree = Tree()
        callback = mock.Mock()
        tree.subscribe(event, callback)
        return tree, callback

    return _make_tree_with_subscriber


class TestIsEmpty:
    def test_new_tree_instance_is_empty(self):
        tree = Tree()

        assert tree.is_empty

    def test_tree_with_panes_is_not_empty(self):
        tree = Tree()

        tree.add_tab()

        assert not tree.is_empty


class TestSplit:
    def test_returns_correct_pane(self):
        tree = Tree()
        p1 = tree.add_tab()

        p2 = tree.split(p1, "x")
        p3 = tree.split(p2, "x")

        assert isinstance(p2, Pane)
        assert p2.id == 5

        assert isinstance(p3, Pane)
        assert p3.id == 6

    def test_split_along_x_axis(self):
        tree = Tree()
        p1 = tree.add_tab()

        tree.split(p1, "x")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                        - p:5 | {x: 0.5, y: 0.02, w: 0.5, h: 0.98}
            """,
        )

    def test_split_along_y_axis(self):
        tree = Tree()
        p1 = tree.add_tab()

        tree.split(p1, "y")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.49}
                        - p:5 | {x: 0.0, y: 0.51, w: 1.0, h: 0.49}
            """,
        )

    def test_subsequent_splits_are_added_under_the_same_split_container(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")

        tree.split(p2, "x")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                        - p:5 | {x: 0.5, y: 0.02, w: 0.25, h: 0.98}
                        - p:6 | {x: 0.75, y: 0.02, w: 0.25, h: 0.98}
            """,
        )

    def test_split_happens_at_correct_position_when_there_are_multiple_splits(self):
        tree = Tree()
        p1 = tree.add_tab()
        tree.split(p1, "x")

        tree.split(p1, "x")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.25, h: 0.98}
                        - p:6 | {x: 0.25, y: 0.02, w: 0.25, h: 0.98}
                        - p:5 | {x: 0.5, y: 0.02, w: 0.5, h: 0.98}
            """,
        )

    def test_can_split_by_arbitrary_ratio(self):
        tree = Tree()
        p1 = tree.add_tab()

        tree.split(p1, "x", 0.8)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.8, h: 0.98}
                        - p:5 | {x: 0.8, y: 0.02, w: 0.2, h: 0.98}
            """,
        )

    @pytest.mark.parametrize("ratio", [-1, -0.1, 1.1, 10])
    def test_when_invalid_ratio_provided_should_raise_error(self, ratio):
        tree = Tree()
        p1 = tree.add_tab()

        err_msg = "Value of `ratio` must be between 0 and 1 inclusive."
        with pytest.raises(ValueError, match=err_msg):
            tree.split(p1, "x", ratio)

    def test_subscribers_are_notified_of_added_nodes(self):
        callback = mock.Mock()
        tree = Tree()
        tree.subscribe(TreeEvent.node_added, callback)

        p1 = tree.add_tab()
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
    def test_y_split_after_x_split_should_put_resulting_splits_under_new_y_split_container(
        self,
    ):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")

        tree.split(p2, "y")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                        - sc.y:6
                            - p:5 | {x: 0.5, y: 0.02, w: 0.5, h: 0.49}
                            - p:7 | {x: 0.5, y: 0.51, w: 0.5, h: 0.49}
            """,
        )

    def test_x_split_after_y_split_should_put_resulting_splits_under_new_x_split_container(
        self,
    ):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "y")

        tree.split(p2, "x")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.49}
                        - sc.x:6
                            - p:5 | {x: 0.0, y: 0.51, w: 0.5, h: 0.49}
                            - p:7 | {x: 0.5, y: 0.51, w: 0.5, h: 0.49}
            """,
        )

    def test_nested_x_split(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")
        p3 = tree.split(p2, "y")

        tree.split(p3, "x")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                        - sc.y:6
                            - p:5 | {x: 0.5, y: 0.02, w: 0.5, h: 0.49}
                            - sc.x:8
                                - p:7 | {x: 0.5, y: 0.51, w: 0.25, h: 0.49}
                                - p:9 | {x: 0.75, y: 0.51, w: 0.25, h: 0.49}
            """,
        )

    def test_nested_y_split(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "y")
        p3 = tree.split(p2, "x")

        tree.split(p3, "y")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.49}
                        - sc.x:6
                            - p:5 | {x: 0.0, y: 0.51, w: 0.5, h: 0.49}
                            - sc.y:8
                                - p:7 | {x: 0.5, y: 0.51, w: 0.5, h: 0.245}
                                - p:9 | {x: 0.5, y: 0.755, w: 0.5, h: 0.245}
            """,
        )


class TestAddTab:
    class TestParameterValidity:
        def test_raises_error_when_tree_is_empty_and_pane_reference_is_provided(self):
            tree = Tree()
            dummy_pane = Pane(UnitRect(0, 0, 1, 1))

            err_msg = "The tree is empty. The provided arguments are invalid."
            with pytest.raises(ValueError, match=err_msg):
                tree.add_tab(at_pane=dummy_pane)

        def test_raises_error_when_tree_is_empty_and_new_level_is_requested(self):
            tree = Tree()

            err_msg = "The tree is empty. The provided arguments are invalid."
            with pytest.raises(ValueError, match=err_msg):
                tree.add_tab(new_level=True)

        def test_raises_error_when_tree_is_empty_and_level_is_specified(self):
            tree = Tree()

            err_msg = "The tree is empty. The provided arguments are invalid."
            with pytest.raises(ValueError, match=err_msg):
                tree.add_tab(level=2)

        def test_raises_error_when_new_level_is_requested_but_pane_reference_not_provided(
            self,
        ):
            tree = Tree()
            tree.add_tab()

            err_msg = (
                "`new_level` requires a reference `at_pane` under which to add tabs"
            )
            with pytest.raises(ValueError, match=err_msg):
                tree.add_tab(new_level=True)

        def test_raises_error_when_level_specified_but_pane_reference_not_provided(
            self,
        ):
            tree = Tree()
            tree.add_tab()

            err_msg = "`level` requires a reference `at_pane`"
            with pytest.raises(ValueError, match=err_msg):
                tree.add_tab(level=2)

        @pytest.mark.parametrize("level", [-5, -1, 0])
        def test_raises_error_when_level_specified_but_is_less_than_1(self, level):
            tree = Tree()
            p1 = tree.add_tab()

            err_msg = "`level` must be 1 or higher"
            with pytest.raises(ValueError, match=err_msg):
                tree.add_tab(p1, level=level)

        def test_raises_error_when_level_specified_but_is_more_than_tree_level(self):
            tree = Tree()

            p1 = tree.add_tab()
            tree.add_tab(p1, new_level=True)
            tree.add_tab(p1, new_level=True)

            err_msg = "`4` is an invalid level. The tree currently only has 3 levels."
            with pytest.raises(ValueError, match=err_msg):
                tree.add_tab(p1, level=4)

    def test_pane_is_returned(self):
        tree = Tree()

        pane = tree.add_tab()

        assert isinstance(pane, Pane)

    def test_when_a_tab_is_created_then_it_has_an_auto_generated_title_based_on_its_index(
        self,
    ):
        tree = Tree()

        p1 = tree.add_tab()
        p2 = tree.add_tab()

        t1 = p1.get_first_ancestor(Tab)
        t2 = p2.get_first_ancestor(Tab)

        assert t1.title == "1"
        assert t2.title == "2"

    def test_when_a_tab_is_created_at_a_nested_level_then_it_has_an_auto_generated_title_based_on_its_index(
        self,
    ):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.add_tab(p1, new_level=True)

        t1_1, _ = p1.get_ancestors(Tab)
        t1_2, _ = p2.get_ancestors(Tab)

        assert t1_1.title == "1"
        assert t1_2.title == "2"

    def test_add_tab_to_empty_tree(self):
        tree = Tree()

        tree.add_tab()

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
            """,
        )

    def test_add_tab_to_non_empty_tree(self):
        tree = Tree()
        tree.add_tab()

        tree.add_tab()

        assert tree_matches_repr(
            tree,
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

    def test_tab_container_has_active_tab(self):
        tree = Tree()

        p1 = tree.add_tab()

        assert tree.is_visible(p1)

    def test_add_tab_at_specified_pane(self):
        tree = Tree()
        tree.add_tab()
        p2 = tree.add_tab()
        tree.add_tab()

        # Current behvavior adds tab at end of provided pane's level of tabs.
        tree.add_tab(p2)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
                - t:5
                    - sc.x:6
                        - p:7 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
                - t:8
                    - sc.x:9
                        - p:10 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
                - t:11
                    - sc.x:12
                        - p:13 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
            """,
        )

    def test_in_nested_tree_adding_tab_without_pane_reference_should_add_at_topmost_tab_level(
        self,
    ):
        tree = Tree()
        p1 = tree.add_tab()
        tree.add_tab(p1, new_level=True)

        tree.add_tab()

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:5
                            - t:6
                                - sc.x:7
                                    - p:4 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
                            - t:8
                                - sc.x:9
                                    - p:10 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
                - t:11
                    - sc.x:12
                        - p:13 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
            """,
        )

    def test_in_nested_tree_adding_tab_at_pane_without_providing_level_params_should_add_at_deepest_level_of_the_pane(
        self,
    ):
        tree = Tree()
        p1 = tree.add_tab()
        tree.add_tab(p1, new_level=True)

        tree.add_tab(p1)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:5
                            - t:6
                                - sc.x:7
                                    - p:4 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
                            - t:8
                                - sc.x:9
                                    - p:10 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
                            - t:11
                                - sc.x:12
                                    - p:13 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
            """,
        )

    def test_add_tab_at_new_level(self):
        tree = Tree()
        p1 = tree.add_tab()

        tree.add_tab(p1, new_level=True)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:5
                            - t:6
                                - sc.x:7
                                    - p:4 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
                            - t:8
                                - sc.x:9
                                    - p:10 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
            """,
        )

    def test_nested_tab_containers_have_active_tab(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.add_tab(p1, new_level=True)

        assert tree.is_visible(p2)

    def test_add_tab_at_multiple_new_levels(self):
        tree = Tree()
        p1 = tree.add_tab()

        p2 = tree.add_tab(p1, new_level=True)
        p3 = tree.add_tab(p2, new_level=True)
        tree.add_tab(p3, new_level=True)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:5
                            - t:6
                                - sc.x:7
                                    - p:4 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
                            - t:8
                                - sc.x:9
                                    - tc:11
                                        - t:12
                                            - sc.x:13
                                                - p:10 | {x: 0.0, y: 0.06, w: 1.0, h: 0.94}
                                        - t:14
                                            - sc.x:15
                                                - tc:17
                                                    - t:18
                                                        - sc.x:19
                                                            - p:16 | {x: 0.0, y: 0.08, w: 1.0, h: 0.92}
                                                    - t:20
                                                        - sc.x:21
                                                            - p:22 | {x: 0.0, y: 0.08, w: 1.0, h: 0.92}
            """,
        )

    def test_add_tab_at_new_level_in_split(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")

        tree.add_tab(p2, new_level=True)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                        - tc:6
                            - t:7
                                - sc.x:8
                                    - p:5 | {x: 0.5, y: 0.04, w: 0.5, h: 0.96}
                            - t:9
                                - sc.x:10
                                    - p:11 | {x: 0.5, y: 0.04, w: 0.5, h: 0.96}
            """,
        )

    def test_add_tab_at_new_level_in_multiple_splits(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "y")
        tree.split(p1, "x")

        tree.add_tab(p2, new_level=True)
        tree.add_tab(p1, new_level=True)

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
                                        - p:4 | {x: 0.0, y: 0.04, w: 0.5, h: 0.47}
                                - t:17
                                    - sc.x:18
                                        - p:19 | {x: 0.0, y: 0.04, w: 0.5, h: 0.47}
                            - p:7 | {x: 0.5, y: 0.02, w: 0.5, h: 0.49}
                        - tc:8
                            - t:9
                                - sc.x:10
                                    - p:5 | {x: 0.0, y: 0.53, w: 1.0, h: 0.47}
                            - t:11
                                - sc.x:12
                                    - p:13 | {x: 0.0, y: 0.53, w: 1.0, h: 0.47}
            """,
        )

    def test_add_tab_at_new_level_at_split_in_nested_tab_level(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")
        p3 = tree.add_tab(p2, new_level=True)
        p4 = tree.split(p3, "y")

        tree.add_tab(p4, new_level=True)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                        - tc:6
                            - t:7
                                - sc.x:8
                                    - p:5 | {x: 0.5, y: 0.04, w: 0.5, h: 0.96}
                            - t:9
                                - sc.y:10
                                    - p:11 | {x: 0.5, y: 0.04, w: 0.5, h: 0.48}
                                    - tc:13
                                        - t:14
                                            - sc.x:15
                                                - p:12 | {x: 0.5, y: 0.54, w: 0.5, h: 0.46}
                                        - t:16
                                            - sc.x:17
                                                - p:18 | {x: 0.5, y: 0.54, w: 0.5, h: 0.46}
            """,
        )

    def test_add_tab_at_arbitrary_level(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.add_tab(p1, new_level=True)
        tree.add_tab(p2, new_level=True)

        # Before this invocation, p1 is at level 2; p2, p3 are at level 3. So if we take
        # p2, we can add at either level 1, level 2 or level 3. We pick level 2.
        tree.add_tab(p2, level=2)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - tc:5
                            - t:6
                                - sc.x:7
                                    - p:4 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
                            - t:8
                                - sc.x:9
                                    - tc:11
                                        - t:12
                                            - sc.x:13
                                                - p:10 | {x: 0.0, y: 0.06, w: 1.0, h: 0.94}
                                        - t:14
                                            - sc.x:15
                                                - p:16 | {x: 0.0, y: 0.06, w: 1.0, h: 0.94}
                            - t:17
                                - sc.x:18
                                    - p:19 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
            """,
        )

    def test_add_tab_at_level_when_different_nest_levels_present_under_different_splits(
        self,
    ):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")

        tree.add_tab(p1, new_level=True)
        p4 = tree.add_tab(p1, new_level=True)
        tree.add_tab(p1, new_level=True)

        tree.add_tab(p2, new_level=True)
        tree.add_tab(p2, new_level=True)

        # Before this invocation, under two top level split panes, we have 4 levels on
        # the left side and 3 levels on the right side. Adding at p4 at level 2 should
        # only add to the 2nd level under the left pane.
        tree.add_tab(p4, level=2)

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
                                                            - p:4 | {x: 0.0, y: 0.08, w: 0.5, h: 0.92}
                                                    - t:21
                                                        - sc.x:22
                                                            - p:23 | {x: 0.0, y: 0.08, w: 0.5, h: 0.92}
                                        - t:15
                                            - sc.x:16
                                                - p:17 | {x: 0.0, y: 0.06, w: 0.5, h: 0.94}
                            - t:9
                                - sc.x:10
                                    - p:11 | {x: 0.0, y: 0.04, w: 0.5, h: 0.96}
                            - t:36
                                - sc.x:37
                                    - p:38 | {x: 0.0, y: 0.04, w: 0.5, h: 0.96}
                        - tc:24
                            - t:25
                                - sc.x:26
                                    - tc:30
                                        - t:31
                                            - sc.x:32
                                                - p:5 | {x: 0.5, y: 0.06, w: 0.5, h: 0.94}
                                        - t:33
                                            - sc.x:34
                                                - p:35 | {x: 0.5, y: 0.06, w: 0.5, h: 0.94}
                            - t:27
                                - sc.x:28
                                    - p:29 | {x: 0.5, y: 0.04, w: 0.5, h: 0.96}
            """,
        )

    def test_subscribers_are_notified_of_added_nodes(self):
        callback = mock.Mock()
        tree = Tree()
        tree.subscribe(TreeEvent.node_added, callback)

        p1 = tree.add_tab()
        sc1, t1, tc1 = p1.get_ancestors()

        p2 = tree.add_tab(p1)
        sc2, t2, _ = p2.get_ancestors()

        p3 = tree.add_tab(p2, new_level=True)
        sc3, t3, tc2, _, _, _ = p3.get_ancestors()

        assert callback.mock_calls == [
            mock.call([tc1, t1, sc1, p1]),
            mock.call([t2, sc2, p2]),
            mock.call([tc2, t3, sc3, p3]),
        ]


class TestSplitsUnderTabs:
    def test_x_split_does_not_affect_dimensions_of_other_tabs(self):
        tree = Tree()
        p1 = tree.add_tab()
        tree.add_tab()
        p3 = tree.add_tab()

        tree.split(p1, "x")
        tree.split(p1, "x")
        tree.split(p3, "x")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.25, h: 0.98}
                        - p:12 | {x: 0.25, y: 0.02, w: 0.25, h: 0.98}
                        - p:11 | {x: 0.5, y: 0.02, w: 0.5, h: 0.98}
                - t:5
                    - sc.x:6
                        - p:7 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
                - t:8
                    - sc.x:9
                        - p:10 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                        - p:13 | {x: 0.5, y: 0.02, w: 0.5, h: 0.98}
            """,
        )

    def test_y_split_does_not_affect_dimensions_of_other_tabs(self):
        tree = Tree()
        p1 = tree.add_tab()
        tree.add_tab()
        p3 = tree.add_tab()

        tree.split(p1, "y")
        tree.split(p1, "y")
        tree.split(p3, "y")

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.245}
                        - p:12 | {x: 0.0, y: 0.265, w: 1.0, h: 0.245}
                        - p:11 | {x: 0.0, y: 0.51, w: 1.0, h: 0.49}
                - t:5
                    - sc.x:6
                        - p:7 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
                - t:8
                    - sc.y:9
                        - p:10 | {x: 0.0, y: 0.02, w: 1.0, h: 0.49}
                        - p:13 | {x: 0.0, y: 0.51, w: 1.0, h: 0.49}
            """,
        )

    def test_x_split_under_nested_tab(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.add_tab(p1, new_level=True)

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
                                    - p:4 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
                            - t:8
                                - sc.x:9
                                    - p:10 | {x: 0.0, y: 0.04, w: 0.5, h: 0.96}
                                    - p:11 | {x: 0.5, y: 0.04, w: 0.5, h: 0.96}
            """,
        )

    def test_y_split_under_nested_tab(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.add_tab(p1, new_level=True)

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
                                    - p:4 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
                            - t:8
                                - sc.y:9
                                    - p:10 | {x: 0.0, y: 0.04, w: 1.0, h: 0.48}
                                    - p:11 | {x: 0.0, y: 0.52, w: 1.0, h: 0.48}
            """,
        )

    def test_nested_splits_under_nested_tabs(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "y")
        tree.split(p1, "x")
        p4 = tree.split(p2, "x")

        tree.add_tab(p1, new_level=True)
        p6 = tree.add_tab(p4, new_level=True)

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
                                            - p:4 | {x: 0.0, y: 0.04, w: 0.25, h: 0.235}
                                            - p:24 | {x: 0.0, y: 0.275, w: 0.25, h: 0.235}
                                        - p:22 | {x: 0.25, y: 0.04, w: 0.25, h: 0.47}
                                - t:13
                                    - sc.x:14
                                        - p:15 | {x: 0.0, y: 0.04, w: 0.5, h: 0.47}
                            - p:7 | {x: 0.5, y: 0.02, w: 0.5, h: 0.49}
                        - sc.x:8
                            - p:5 | {x: 0.0, y: 0.51, w: 0.5, h: 0.49}
                            - tc:16
                                - t:17
                                    - sc.x:18
                                        - p:9 | {x: 0.5, y: 0.53, w: 0.5, h: 0.47}
                                - t:19
                                    - sc.x:20
                                        - sc.y:26
                                            - p:21 | {x: 0.5, y: 0.53, w: 0.25, h: 0.235}
                                            - p:27 | {x: 0.5, y: 0.765, w: 0.25, h: 0.235}
                                        - p:25 | {x: 0.75, y: 0.53, w: 0.25, h: 0.47}
            """,
        )


class TestResize:
    @pytest.mark.parametrize("axis", ["x", "y"])
    @pytest.mark.parametrize("amount", [-10, -2, -1.01, 1.01, 2, 10])
    def test_amount_must_be_in_valid_range(self, axis, amount):
        tree = Tree()
        p1 = tree.add_tab()
        tree.split(p1, "x")

        err_msg = "`amount` must be between -1 and 1"
        with pytest.raises(ValueError, match=err_msg):
            tree.resize(p1, axis, amount)

    def test_resize_on_x_axis_by_positive_amount(self):
        tree = Tree()
        p1 = tree.add_tab()
        tree.split(p1, "x")

        tree.resize(p1, "x", 0.1)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.6, h: 0.98}
                        - p:5 | {x: 0.6, y: 0.02, w: 0.4, h: 0.98}
            """,
        )

    def test_resize_on_x_axis_by_negative_amount(self):
        tree = Tree()
        p1 = tree.add_tab()
        tree.split(p1, "x")

        tree.resize(p1, "x", -0.1)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.4, h: 0.98}
                        - p:5 | {x: 0.4, y: 0.02, w: 0.6, h: 0.98}
            """,
        )

    def test_resize_on_y_axis_by_positive_amount(self):
        tree = Tree()
        p1 = tree.add_tab()
        tree.split(p1, "y")

        tree.resize(p1, "y", 0.1)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.59}
                        - p:5 | {x: 0.0, y: 0.61, w: 1.0, h: 0.39}
            """,
        )

    def test_resize_on_y_axis_by_negative_amount(self):
        tree = Tree()
        p1 = tree.add_tab()
        tree.split(p1, "y")

        tree.resize(p1, "y", -0.1)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.39}
                        - p:5 | {x: 0.0, y: 0.41, w: 1.0, h: 0.59}
            """,
        )

    def test_resize_on_x_axis_should_modify_right_border_if_not_last_pane(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")
        tree.split(p2, "x")

        tree.resize(p2, "x", 0.1)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                        - p:5 | {x: 0.5, y: 0.02, w: 0.35, h: 0.98}
                        - p:6 | {x: 0.85, y: 0.02, w: 0.15, h: 0.98}
            """,
        )

    def test_resize_on_x_axis_should_modify_left_border_if_last_pane(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")
        p3 = tree.split(p2, "x")

        tree.resize(p3, "x", 0.1)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                        - p:5 | {x: 0.5, y: 0.02, w: 0.35, h: 0.98}
                        - p:6 | {x: 0.85, y: 0.02, w: 0.15, h: 0.98}
            """,
        )

    def test_resize_on_y_axis_should_modify_bottom_border_if_not_last_pane(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "y")
        tree.split(p2, "y")

        tree.resize(p2, "y", 0.1)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.49}
                        - p:5 | {x: 0.0, y: 0.51, w: 1.0, h: 0.345}
                        - p:6 | {x: 0.0, y: 0.855, w: 1.0, h: 0.145}
            """,
        )

    def test_resize_on_y_axis_should_modify_top_border_if_last_pane(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "y")
        p3 = tree.split(p2, "y")

        tree.resize(p3, "y", 0.1)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.y:3
                        - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.49}
                        - p:5 | {x: 0.0, y: 0.51, w: 1.0, h: 0.345}
                        - p:6 | {x: 0.0, y: 0.855, w: 1.0, h: 0.145}
            """,
        )

    @pytest.mark.parametrize("axis", ["x", "y"])
    @pytest.mark.parametrize("amount", [0.1, -0.1])
    def test_no_op_when_trying_to_resize_lone_pane_under_top_level_tabs(
        self, axis, amount
    ):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.add_tab()
        p3 = tree.add_tab()

        tree.resize(p1, axis, amount)
        tree.resize(p2, axis, amount)
        tree.resize(p3, axis, amount)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
                - t:5
                    - sc.x:6
                        - p:7 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
                - t:8
                    - sc.x:9
                        - p:10 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
            """,
        )

    @pytest.mark.parametrize("amount", [0.1, -0.1])
    def test_no_op_when_trying_to_resize_top_level_panes_under_root_tab_container_against_axis(
        self, amount
    ):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")

        tree.resize(p1, "y", amount)
        tree.resize(p2, "y", amount)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                        - p:5 | {x: 0.5, y: 0.02, w: 0.5, h: 0.98}
            """,
        )

    class TestResizeInvolvingNestedSplits:
        def test_resizing_nested_pane_along_axis_should_only_affect_the_pane_and_its_sibling(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            tree.split(p1, "x")
            tree.split(p1, "y")
            p4 = tree.split(p1, "x")
            tree.split(p4, "x")

            # Resizing `p:9` along container axis should only affect `p:9` and `p:10`
            tree.resize(p4, "x", 0.05)

            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - sc.y:6
                                - sc.x:8
                                    - p:4 | {x: 0.0, y: 0.02, w: 0.25, h: 0.49}
                                    - p:9 | {x: 0.25, y: 0.02, w: 0.175, h: 0.49}
                                    - p:10 | {x: 0.425, y: 0.02, w: 0.075, h: 0.49}
                                - p:7 | {x: 0.0, y: 0.51, w: 0.5, h: 0.49}
                            - p:5 | {x: 0.5, y: 0.02, w: 0.5, h: 0.98}
                """,
            )

        def test_resizing_nested_pane_against_axis_should_resize_all_panes_in_enclosing_container_and_sibling_of_the_container(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            tree.split(p1, "x")
            tree.split(p1, "y")
            p4 = tree.split(p1, "x")
            tree.split(p4, "x")

            # Resizing `p:9` against container axis should affect all panes in enclosing
            # container - `p:4`, `p:9`, `p:10`; and the sibling of the container - `p:7`
            tree.resize(p4, "y", 0.1)

            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - sc.y:6
                                - sc.x:8
                                    - p:4 | {x: 0.0, y: 0.02, w: 0.25, h: 0.59}
                                    - p:9 | {x: 0.25, y: 0.02, w: 0.125, h: 0.59}
                                    - p:10 | {x: 0.375, y: 0.02, w: 0.125, h: 0.59}
                                - p:7 | {x: 0.0, y: 0.61, w: 0.5, h: 0.39}
                            - p:5 | {x: 0.5, y: 0.02, w: 0.5, h: 0.98}
                """,
            )

        class TestWhenOperationalSiblingIsContainerBeingGrown:
            def test_should_grow_nested_items_that_are_along_resize_axis_in_proportion_to_their_size_along_that_axis(
                self,
            ):
                tree = Tree()
                p1 = tree.add_tab()
                p2 = tree.split(p1, "x")
                p3 = tree.split(p2, "y")
                tree.split(p3, "x")
                tree.split(p3, "x")

                # Shrinking `p:4` should grow all panes in `sc.y:6`.
                # In `sc.y:6`, those in `sc.x:8` should be grown by fractions of 0.1
                # proportional to their size. From the 0.1 amount, `p:7` grows by 0.025,
                # `p:10` grows by 0.025, `p:9` grows by 0.05. The start coordinates are
                # also adjusted.
                tree.resize(p1, "x", -0.1)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0.0, y: 0.02, w: 0.4, h: 0.98}
                                - sc.y:6
                                    - p:5 | {x: 0.4, y: 0.02, w: 0.6, h: 0.49}
                                    - sc.x:8
                                        - p:7 | {x: 0.4, y: 0.51, w: 0.15, h: 0.49}
                                        - p:10 | {x: 0.55, y: 0.51, w: 0.15, h: 0.49}
                                        - p:9 | {x: 0.7, y: 0.51, w: 0.3, h: 0.49}
                    """,
                )

            def test_should_grow_nested_items_that_are_against_resize_axis_by_the_same_amount(
                self,
            ):
                tree = Tree()
                p1 = tree.add_tab()
                p2 = tree.split(p1, "x")
                p3 = tree.split(p2, "y")
                p4 = tree.split(p3, "x")
                tree.split(p3, "y")
                tree.split(p4, "y")

                # Shrinking `p:4` would grow all panes in `sc.y:6`.
                # Children of `sc.x:8` that are along the resize axis get 0.05 each.
                # Then children of `sc.y:10` and `sc.y:12` are all resized equally by
                # that amount.
                tree.resize(p1, "x", -0.1)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0.0, y: 0.02, w: 0.4, h: 0.98}
                                - sc.y:6
                                    - p:5 | {x: 0.4, y: 0.02, w: 0.6, h: 0.49}
                                    - sc.x:8
                                        - sc.y:10
                                            - p:7 | {x: 0.4, y: 0.51, w: 0.3, h: 0.245}
                                            - p:11 | {x: 0.4, y: 0.755, w: 0.3, h: 0.245}
                                        - sc.y:12
                                            - p:9 | {x: 0.7, y: 0.51, w: 0.3, h: 0.245}
                                            - p:13 | {x: 0.7, y: 0.755, w: 0.3, h: 0.245}
                    """,
                )

        class TestWhenOperationalSiblingIsContainerBeingShrunk:
            def test_should_shrink_nested_items_that_are_along_resize_axis_in_proportion_to_their_capacity_to_shrink_along_that_axis(
                self,
            ):
                tree = Tree()
                p1 = tree.add_tab()
                p2 = tree.split(p1, "x")
                p3 = tree.split(p2, "y")
                tree.split(p3, "x")
                tree.split(p3, "x")

                # Shrinking `p:4` should shrink all panes in `sc.y:6`.
                # In `sc.y:6`, those in `sc.x:8` should be shrunk by fractions of 0.1
                # proportional to their capacity to shrink.
                # `p:7` shrinks by: (0.125 - 0.05)/0.35 ~= 0.0214
                # `p:10` shrinks by: (0.125 - 0.05)/0.35 ~= 0.0214
                # `p:9` shrinks by: (0.25 - 0.05)/0.35 ~= 0.0571
                tree.resize(p1, "x", 0.1)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0.0, y: 0.02, w: 0.6, h: 0.98}
                                - sc.y:6
                                    - p:5 | {x: 0.6, y: 0.02, w: 0.4, h: 0.49}
                                    - sc.x:8
                                        - p:7 | {x: 0.6, y: 0.51, w: 0.1036, h: 0.49}
                                        - p:10 | {x: 0.7036, y: 0.51, w: 0.1036, h: 0.49}
                                        - p:9 | {x: 0.8071, y: 0.51, w: 0.1929, h: 0.49}
                    """,
                )

            def test_should_shrink_nested_items_that_are_against_resize_axis_by_the_same_amount(
                self,
            ):
                tree = Tree()
                p1 = tree.add_tab()
                p2 = tree.split(p1, "x")
                tree.split(p2, "y")

                # Resize `p:4` should shrink all panes in `sc.y:6` by the full resize amount
                tree.resize(p1, "x", 0.1)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0.0, y: 0.02, w: 0.6, h: 0.98}
                                - sc.y:6
                                    - p:5 | {x: 0.6, y: 0.02, w: 0.4, h: 0.49}
                                    - p:7 | {x: 0.6, y: 0.51, w: 0.4, h: 0.49}
                    """,
                )

            def test_when_all_nested_panes_are_at_min_size_without_any_space_left_to_shrink_it_should_be_a_no_op(
                self,
            ):
                tree = Tree()
                p1 = tree.add_tab()
                p2 = tree.split(p1, "x", 0.8)
                p3 = tree.split(p2, "y")
                p4 = tree.split(p3, "x")
                tree.split(p3, "x")
                tree.split(p4, "x")

                # All of `p:7`, `p:10`, `p:9`, `p:11` are at min size. Since they cannot
                # be shrunk further, they should block the resize of the entire
                # `sc.y:6` operational sibling branch, resulting in a no-op.
                tree.resize(p1, "x", 0.1)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0.0, y: 0.02, w: 0.8, h: 0.98}
                                - sc.y:6
                                    - p:5 | {x: 0.8, y: 0.02, w: 0.2, h: 0.49}
                                    - sc.x:8
                                        - p:7 | {x: 0.8, y: 0.51, w: 0.05, h: 0.49}
                                        - p:10 | {x: 0.85, y: 0.51, w: 0.05, h: 0.49}
                                        - p:9 | {x: 0.9, y: 0.51, w: 0.05, h: 0.49}
                                        - p:11 | {x: 0.95, y: 0.51, w: 0.05, h: 0.49}
                    """,
                )

            def test_when_nested_panes_cannot_consume_all_of_the_shrink_amount_they_should_consume_as_much_of_the_amount_as_possible(
                self,
            ):
                tree = Tree()
                p1 = tree.add_tab()
                p2 = tree.split(p1, "x", 0.8)
                p3 = tree.split(p2, "y")
                tree.split(p3, "x")

                # `p:7` and `p:9` have 0.1 width each. They should be able to together
                # consume 0.1 of the requested 0.2 to shrink and reach min size.
                tree.resize(p1, "x", 0.2)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0.0, y: 0.02, w: 0.9, h: 0.98}
                                - sc.y:6
                                    - p:5 | {x: 0.9, y: 0.02, w: 0.1, h: 0.49}
                                    - sc.x:8
                                        - p:7 | {x: 0.9, y: 0.51, w: 0.05, h: 0.49}
                                        - p:9 | {x: 0.95, y: 0.51, w: 0.05, h: 0.49}
                    """,
                )

    class TestResizeInvolvingTabs:
        def test_resizing_panes_under_one_tab_does_not_affect_panes_under_other_tabs(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            tree.split(p2, "y")
            p4 = tree.add_tab()
            p5 = tree.split(p4, "x")
            tree.split(p5, "y")

            tree.resize(p1, "x", 0.1)
            tree.resize(p2, "y", 0.1)

            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - p:4 | {x: 0.0, y: 0.02, w: 0.6, h: 0.98}
                            - sc.y:6
                                - p:5 | {x: 0.6, y: 0.02, w: 0.4, h: 0.59}
                                - p:7 | {x: 0.6, y: 0.61, w: 0.4, h: 0.39}
                    - t:8
                        - sc.x:9
                            - p:10 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                            - sc.y:12
                                - p:11 | {x: 0.5, y: 0.02, w: 0.5, h: 0.49}
                                - p:13 | {x: 0.5, y: 0.51, w: 0.5, h: 0.49}
                """,
            )

        def test_resizing_panes_under_nested_tab_container_does_not_affect_panes_under_other_tabs_in_the_tab_container(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.add_tab(p1, new_level=True)
            p3 = tree.split(p2, "x")
            p4 = tree.add_tab(p3, new_level=True)
            p5 = tree.split(p4, "x")

            tree.resize(p5, "x", 0.1)

            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - tc:5
                                - t:6
                                    - sc.x:7
                                        - p:4 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
                                - t:8
                                    - sc.x:9
                                        - p:10 | {x: 0.0, y: 0.04, w: 0.5, h: 0.96}
                                        - tc:12
                                            - t:13
                                                - sc.x:14
                                                    - p:11 | {x: 0.5, y: 0.06, w: 0.5, h: 0.94}
                                            - t:15
                                                - sc.x:16
                                                    - p:17 | {x: 0.5, y: 0.06, w: 0.35, h: 0.94}
                                                    - p:18 | {x: 0.85, y: 0.06, w: 0.15, h: 0.94}
                """,
            )

        def test_when_operational_sibling_is_tab_container_all_its_panes_under_all_tabs_against_resize_axis_get_resized_by_full_amount(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.add_tab(p2, new_level=True)
            p4 = tree.split(p3, "y")
            tree.split(p4, "y")

            tree.resize(p1, "x", 0.1)

            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - p:4 | {x: 0.0, y: 0.02, w: 0.6, h: 0.98}
                            - tc:6
                                - t:7
                                    - sc.x:8
                                        - p:5 | {x: 0.6, y: 0.04, w: 0.4, h: 0.96}
                                - t:9
                                    - sc.y:10
                                        - p:11 | {x: 0.6, y: 0.04, w: 0.4, h: 0.48}
                                        - p:12 | {x: 0.6, y: 0.52, w: 0.4, h: 0.24}
                                        - p:13 | {x: 0.6, y: 0.76, w: 0.4, h: 0.24}
                """,
            )

        def test_resizing_lone_pane_under_nested_tab_should_resize_entire_tab_container(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            tree.split(p1, "x")
            p3 = tree.add_tab(p1, new_level=True)

            # Splits under first sub-tab. Second tab has lone pane p3.
            p4 = tree.split(p1, "x")
            tree.split(p4, "y")

            tree.resize(p3, "x", 0.1)

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
                                        - p:4 | {x: 0.0, y: 0.04, w: 0.3, h: 0.96}
                                        - sc.y:13
                                            - p:12 | {x: 0.3, y: 0.04, w: 0.3, h: 0.48}
                                            - p:14 | {x: 0.3, y: 0.52, w: 0.3, h: 0.48}
                                - t:9
                                    - sc.x:10
                                        - p:11 | {x: 0.0, y: 0.04, w: 0.6, h: 0.96}
                            - p:5 | {x: 0.6, y: 0.02, w: 0.4, h: 0.98}
                """,
            )

        def test_when_a_sole_pane_under_a_nested_tc_is_resized_then_it_gets_resized_as_if_it_were_a_pane_directly_under_container_of_said_tc(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")
            p4 = tree.add_tab(p3, new_level=True)

            tree.resize(p4, "y", -0.1)

            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                            - sc.y:6
                                - p:5 | {x: 0.5, y: 0.02, w: 0.5, h: 0.39}
                                - tc:8
                                    - t:9
                                        - sc.x:10
                                            - p:7 | {x: 0.5, y: 0.43, w: 0.5, h: 0.57}
                                    - t:11
                                        - sc.x:12
                                            - p:13 | {x: 0.5, y: 0.43, w: 0.5, h: 0.57}
                """,
            )

        def test_resizing_top_level_pane_with_siblings_under_nested_tab_along_axis_should_only_affect_the_pane_and_its_sibling(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            tree.split(p1, "x")
            p3 = tree.add_tab(p1, new_level=True)
            p4 = tree.split(p3, "x")

            tree.resize(p4, "x", 0.1)

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
                                        - p:4 | {x: 0.0, y: 0.04, w: 0.5, h: 0.96}
                                - t:9
                                    - sc.x:10
                                        - p:11 | {x: 0.0, y: 0.04, w: 0.35, h: 0.96}
                                        - p:12 | {x: 0.35, y: 0.04, w: 0.15, h: 0.96}
                            - p:5 | {x: 0.5, y: 0.02, w: 0.5, h: 0.98}
                """,
            )

        def test_resizing_top_level_pane_with_siblings_under_nested_tab_against_axis_should_affect_the_entire_tab_container_and_the_tab_containers_sibling(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            tree.split(p1, "x")
            p3 = tree.add_tab(p1, new_level=True)
            p4 = tree.split(p3, "y")

            tree.resize(p4, "x", 0.1)

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
                                        - p:4 | {x: 0.0, y: 0.04, w: 0.6, h: 0.96}
                                - t:9
                                    - sc.y:10
                                        - p:11 | {x: 0.0, y: 0.04, w: 0.6, h: 0.48}
                                        - p:12 | {x: 0.0, y: 0.52, w: 0.6, h: 0.48}
                            - p:5 | {x: 0.6, y: 0.02, w: 0.4, h: 0.98}
                """,
            )

        def test_when_tab_container_is_resized_on_y_axis_then_the_tab_bar_height_is_also_considered(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")
            tree.add_tab(p3, new_level=True)

            tree.resize(p2, "y", -0.1)

            assert tree_matches_repr(
                tree,
                """
                - tc:1
                    - t:2
                        - sc.x:3
                            - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                            - sc.y:6
                                - p:5 | {x: 0.5, y: 0.02, w: 0.5, h: 0.39}
                                - tc:8
                                    - t:9
                                        - sc.x:10
                                            - p:7 | {x: 0.5, y: 0.43, w: 0.5, h: 0.57}
                                    - t:11
                                        - sc.x:12
                                            - p:13 | {x: 0.5, y: 0.43, w: 0.5, h: 0.57}
                """,
            )


class TestRemove:
    def test_when_all_panes_are_removed_then_tree_is_empty(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.add_tab(p1)
        p3 = tree.split(p2, "x")
        p4 = tree.split(p3, "y")

        tree.remove(p1)
        tree.remove(p2)
        tree.remove(p3)
        tree.remove(p4)

        assert tree.is_empty

    def test_when_operational_sibling_is_pane_then_it_is_returned_as_next_focus_node(
        self,
    ):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")

        p = tree.remove(p1)

        assert p is p2

    def test_when_operational_sibling_is_sc_then_its_mru_pane_is_returned_as_next_focus_node(
        self,
    ):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")
        p3 = tree.split(p2, "y")
        tree.split(p3, "y")

        tree.focus(p3)

        p = tree.remove(p1)

        assert p is p3

    def test_when_operational_sibling_is_tc_then_its_mru_pane_is_returned_as_next_focus_node(
        self,
    ):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")
        p3 = tree.add_tab(p2, new_level=True)
        p4 = tree.split(p2, "y")

        tree.focus(p4)

        p = tree.remove(p3)

        assert p is p4

    def test_when_tree_becomes_empty_then_returns_none_as_nothing_left_for_subsequent_focus(
        self,
    ):
        tree = Tree()
        p1 = tree.add_tab()
        p = tree.remove(p1)

        assert p is None

    def test_when_any_pane_except_last_pane_in_container_is_removed_then_right_sibling_consumes_space(
        self,
    ):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")
        tree.split(p2, "x")

        tree.remove(p2)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                        - p:6 | {x: 0.5, y: 0.02, w: 0.5, h: 0.98}
            """,
        )

    def test_when_last_pane_in_container_is_removed_then_left_sibling_consumes_space(
        self,
    ):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")
        p3 = tree.split(p2, "x")

        tree.remove(p3)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:2
                    - sc.x:3
                        - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                        - p:5 | {x: 0.5, y: 0.02, w: 0.5, h: 0.98}
            """,
        )

    def test_when_sibling_that_consumes_space_has_nested_items_then_they_are_grown_in_proportion_to_their_respective_sizes(
        self,
    ):
        tree = Tree()
        p1 = tree.add_tab()
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
                            - p:4 | {x: 0.0, y: 0.02, w: 0.2, h: 0.98}
                            - sc.y:7
                                - p:6 | {x: 0.2, y: 0.02, w: 0.8, h: 0.49}
                                - sc.x:9
                                    - p:8 | {x: 0.2, y: 0.51, w: 0.4, h: 0.49}
                                    - p:10 | {x: 0.6, y: 0.51, w: 0.2, h: 0.49}
                                    - p:11 | {x: 0.8, y: 0.51, w: 0.2, h: 0.49}
                """,
        )

    def test_removal_in_nested_container(self, make_tree_with_subscriber):
        tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)

        p1 = tree.add_tab()
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
                        - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                        - sc.y:6
                            - p:5 | {x: 0.5, y: 0.02, w: 0.5, h: 0.49}
                            - p:8 | {x: 0.5, y: 0.51, w: 0.5, h: 0.49}
            """,
        )

        assert callback.mock_calls == [mock.call([p3])]

    def test_when_last_pane_under_tab_is_removed_then_the_tab_is_removed(
        self, make_tree_with_subscriber
    ):
        tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)

        p1 = tree.add_tab()
        sc1, t1, _ = p1.get_ancestors()
        tree.add_tab()

        tree.remove(p1)

        assert tree_matches_repr(
            tree,
            """
            - tc:1
                - t:5
                    - sc.x:6
                        - p:7 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
            """,
        )

        assert callback.mock_calls == [
            mock.call([p1, sc1, t1]),
        ]

    def test_when_last_pane_under_last_tab_of_tab_container_is_removed_then_then_tab_container_is_removed(
        self, make_tree_with_subscriber
    ):
        tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)

        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")
        p3 = tree.add_tab(p2, new_level=True)

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
                        - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
            """,
        )

        assert callback.mock_calls == [
            mock.call([p2, sc1, t1]),
            mock.call([p3, sc2, t2, tc]),
        ]

    def test_tab_removal_works_in_nested_tabs(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.add_tab(p1, new_level=True)
        tree.add_tab(p2)

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
                                    - p:4 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
                            - t:11
                                - sc.x:12
                                    - p:13 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
            """,
        )

    def test_when_penultimate_tab_is_removed_from_nested_tab_level_then_the_nested_tab_level_is_maintained_without_the_last_tab_being_merged_upwards(
        self,
    ):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.add_tab(p1, new_level=True)

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
                                    - p:4 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
            """,
        )

    def test_subscribers_are_notified_of_removed_nodes_in_the_order_they_are_removed(
        self, make_tree_with_subscriber
    ):
        tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)

        p1 = tree.add_tab()
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
                p1 = tree.add_tab()
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
                                - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                                - p:5 | {x: 0.5, y: 0.02, w: 0.5, h: 0.98}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p3, sc]),
                ]

            def test_when_n1_n2_n3_chain_is_t_sc_sc_then_n1_and_n3_are_linked(
                self, make_tree_with_subscriber
            ):
                tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)
                p1 = tree.add_tab()
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
                                - p:5 | {x: 0.0, y: 0.02, w: 1.0, h: 0.49}
                                - p:7 | {x: 0.0, y: 0.51, w: 1.0, h: 0.49}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p1, sc]),
                ]

            def test_when_n1_n2_n3_chain_is_sc_sc_sc_then_n1_absorbs_children_of_n3(
                self, make_tree_with_subscriber
            ):
                tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)
                p1 = tree.add_tab()
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
                                - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                                - p:7 | {x: 0.5, y: 0.02, w: 0.25, h: 0.98}
                                - p:9 | {x: 0.75, y: 0.02, w: 0.25, h: 0.98}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p2, sc_x, sc_y]),
                ]

            def test_when_n1_n2_n3_chain_is_sc_sc_tc_then_n1_and_n3_are_linked(
                self, make_tree_with_subscriber
            ):
                tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)
                p1 = tree.add_tab()
                p2 = tree.split(p1, "x")
                p3 = tree.split(p2, "y")
                tree.add_tab(p3, new_level=True)

                tree.remove(p2)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                                - tc:8
                                    - t:9
                                        - sc.x:10
                                            - p:7 | {x: 0.5, y: 0.04, w: 0.5, h: 0.96}
                                    - t:11
                                        - sc.x:12
                                            - p:13 | {x: 0.5, y: 0.04, w: 0.5, h: 0.96}
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
                p1 = tree.add_tab()
                p2 = tree.split(p1, "x")

                tree.remove(p2)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p2]),
                ]

            def test_when_n1_n2_n3_chain_is_sc_tc_t_then_no_pruning_happens(
                self, make_tree_with_subscriber
            ):
                tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)
                p1 = tree.add_tab()
                p2 = tree.split(p1, "x")
                p3 = tree.add_tab(p2, new_level=True)
                sc, t, _, _, _, _ = p3.get_ancestors()

                tree.remove(p3)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0.0, y: 0.02, w: 0.5, h: 0.98}
                                - tc:6
                                    - t:7
                                        - sc.x:8
                                            - p:5 | {x: 0.5, y: 0.04, w: 0.5, h: 0.96}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p3, sc, t]),
                ]

            def test_when_n1_n2_n3_chain_is_none_tc_t_then_no_pruning_happens(
                self, make_tree_with_subscriber
            ):
                tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)
                tree.add_tab()
                p2 = tree.add_tab()
                sc, t, _ = p2.get_ancestors()

                tree.remove(p2)

                assert tree_matches_repr(
                    tree,
                    """
                    - tc:1
                        - t:2
                            - sc.x:3
                                - p:4 | {x: 0.0, y: 0.02, w: 1.0, h: 0.98}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p2, sc, t]),
                ]

            def test_when_n1_n2_n3_chain_is_t_sc_tc_then_no_pruning_happens(
                self, make_tree_with_subscriber
            ):
                tree, callback = make_tree_with_subscriber(TreeEvent.node_removed)
                p1 = tree.add_tab()
                p2 = tree.split(p1, "x")
                tree.add_tab(p2, new_level=True)

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
                                            - p:5 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
                                    - t:9
                                        - sc.x:10
                                            - p:11 | {x: 0.0, y: 0.04, w: 1.0, h: 0.96}
                    """,
                )

                assert callback.mock_calls == [
                    mock.call([p1]),
                ]


class TestFocus:
    def test_activates_tab_chain_of_focused_pane(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.add_tab(p1)
        p3 = tree.split(p2, "x")
        p4 = tree.add_tab(p3, new_level=True)
        p5 = tree.split(p4, "x")

        tree.focus(p5)

        tc2, tc1 = p5.get_ancestors(TabContainer)
        t2, t1 = p5.get_ancestors(Tab)

        assert tc2.active_child is t2
        assert tc1.active_child is t1

    def test_deactivates_tab_chain_of_unfocused_pane(self):
        tree = Tree()
        p1 = tree.add_tab()
        p2 = tree.split(p1, "x")
        p3 = tree.add_tab(p2, new_level=True)
        tree.focus(p3)

        p4 = tree.add_tab(p1)
        p5 = tree.split(p4, "x")
        p6 = tree.add_tab(p5, new_level=True)

        tree.focus(p6)

        tc2, tc1 = p3.get_ancestors(TabContainer)
        t2, t1 = p3.get_ancestors(Tab)

        assert tc2.active_child is t2
        assert tc1.active_child is not t1


class TestMotions:
    class TestRight:
        def test_motion_along_axis(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "x")

            assert tree.right(p2) is p3

        def test_motion_along_axis_in_nested_level(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")
            p4 = tree.split(p3, "x")

            assert tree.right(p3) is p4

        def test_motion_against_axis(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p1, "y")

            assert tree.right(p3, wrap=False) is p2

        def test_motion_against_axis_in_nested_level(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")
            p4 = tree.split(p3, "x")
            p5 = tree.split(p3, "y")

            assert tree.right(p5) is p4

        def test_when_wrap_is_true_and_pane_is_at_edge_of_screen_then_pane_from_other_edge_of_screen_is_returned(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "x")

            assert tree.right(p3, wrap=True) is p1

        def test_when_wrap_is_true_and_pane_is_its_own_sibling_then_the_pane_itself_is_returned(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            tree.split(p2, "x")

            assert tree.right(p1, wrap=True) is p1

        def test_when_wrap_is_false_and_pane_is_at_edge_of_screen_then_the_pane_itself_is_returned(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "x")

            assert tree.right(p3, wrap=False) is p3

        def test_when_there_are_multiple_adjacent_panes_then_the_most_recently_focused_one_is_chosen(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")
            p4 = tree.split(p3, "y")
            p5 = tree.split(p4, "y")
            tree.focus(p5)
            tree.focus(p3)
            tree.focus(p4)

            assert tree.right(p1) is p4

        def test_non_adjacent_panes_further_away_in_the_requested_direction_are_not_considered(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x", Pane.min_size * 2)
            p3 = tree.split(p1, "x")

            tree.focus(p3)
            assert tree.right(p1) is p3
            tree.focus(p2)
            assert tree.right(p1) is p3

        def test_adjacent_panes_that_only_partly_share_borders_are_candidates(self):
            tree = Tree()
            p1 = tree.add_tab()
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
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
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
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.add_tab(p2, new_level=True)
            p4 = tree.add_tab(p3)
            tree.focus(p4)

            assert tree.right(p1) is p4

        def test_deeply_nested_adjacent_panes_under_different_super_nodes(self):
            tree = Tree()
            p1 = tree.add_tab()
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
        def test_motion_along_axis(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            tree.split(p2, "x")

            assert tree.left(p2) is p1

        def test_motion_along_axis_in_nested_level(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")
            p4 = tree.split(p3, "x")

            assert tree.left(p4) is p3

        def test_motion_against_axis(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")

            assert tree.left(p3, wrap=False) is p1

        def test_motion_against_axis_in_nested_level(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "y")
            p4 = tree.split(p3, "x")
            p5 = tree.split(p4, "y")

            assert tree.left(p5) is p3

        def test_when_wrap_is_true_and_pane_is_at_edge_of_screen_then_pane_from_other_edge_of_screen_is_returned(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p2, "x")

            assert tree.left(p1, wrap=True) is p3

        def test_when_wrap_is_true_and_pane_is_its_own_sibling_then_the_pane_itself_is_returned(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            tree.split(p2, "x")

            assert tree.left(p1, wrap=True) is p1

        def test_when_wrap_is_false_and_pane_is_at_edge_of_screen_then_the_pane_itself_is_returned(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            tree.split(p2, "x")

            assert tree.left(p1, wrap=False) is p1

        def test_when_there_are_multiple_adjacent_panes_then_the_most_recently_focused_one_is_chosen(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.split(p1, "y")
            p4 = tree.split(p3, "y")
            p5 = tree.split(p4, "y")
            tree.focus(p5)
            tree.focus(p3)
            tree.focus(p4)

            assert tree.left(p2) is p4

        def test_non_adjacent_panes_further_away_in_the_requested_direction_are_not_considered(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x", 1 - (Pane.min_size * 2))
            p3 = tree.split(p2, "x")

            tree.focus(p2)
            assert tree.left(p3) is p2
            tree.focus(p1)
            assert tree.left(p3) is p2

        def test_adjacent_panes_that_only_partly_share_borders_are_candidates(self):
            tree = Tree()
            p1 = tree.add_tab()
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
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
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
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.add_tab(p1, new_level=True)
            p4 = tree.add_tab(p3)
            tree.focus(p4)

            assert tree.left(p2) is p4

        def test_deeply_nested_adjacent_panes_in_different_super_containers(self):
            tree = Tree()
            p1 = tree.add_tab()
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
        def test_motion_along_axis(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "y")

            assert tree.down(p2) is p3

        def test_motion_along_axis_in_nested_level(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "x")
            p4 = tree.split(p3, "y")

            assert tree.down(p3) is p4

        def test_motion_against_axis(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p1, "x")

            assert tree.down(p3, wrap=False) is p2

        def test_motion_against_axis_in_nested_level(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "x")
            p4 = tree.split(p3, "y")
            p5 = tree.split(p3, "x")

            assert tree.down(p5) is p4

        def test_when_wrap_is_true_and_pane_is_at_edge_of_screen_then_pane_from_other_edge_of_screen_is_returned(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "y")

            assert tree.down(p3, wrap=True) is p1

        def test_when_wrap_is_true_and_pane_is_its_own_sibling_then_the_pane_itself_is_returned(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            tree.split(p2, "y")

            assert tree.down(p1, wrap=True) is p1

        def test_when_wrap_is_false_and_pane_is_at_edge_of_screen_then_the_pane_itself_is_returned(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "y")

            assert tree.down(p3, wrap=False) is p3

        def test_when_there_are_multiple_adjacent_panes_then_the_most_recently_focused_one_is_chosen(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "x")
            p4 = tree.split(p3, "x")
            p5 = tree.split(p4, "x")
            tree.focus(p5)
            tree.focus(p3)
            tree.focus(p4)

            assert tree.down(p1) is p4

        def test_non_adjacent_panes_further_away_in_the_requested_direction_are_not_considered(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y", Pane.min_size * 2)
            p3 = tree.split(p1, "y")

            tree.focus(p3)
            assert tree.down(p1) is p3
            tree.focus(p2)
            assert tree.down(p1) is p3

        def test_adjacent_panes_that_only_partly_share_borders_are_candidates(self):
            tree = Tree()
            p1 = tree.add_tab()
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
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
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
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            p3 = tree.add_tab(p2, new_level=True)
            p4 = tree.add_tab(p3)
            tree.focus(p4)

            assert tree.down(p1) is p4

        def test_deeply_nested_adjacent_panes_in_different_super_containers(self):
            tree = Tree()
            p1 = tree.add_tab()
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
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            tree.split(p2, "x")

            p4 = tree.add_tab(p2, new_level=True)
            p5 = tree.add_tab(p4, new_level=True)
            p6 = tree.add_tab(p5, new_level=True)

            tree.focus(p6)

            # p6 is still the most relevant adjacent pane downwards from p1, despite it
            # being 'further' away vertically than p3, due to the many tab bars in
            # between.
            assert tree.down(p1) is p6

    class TestUp:
        def test_motion_along_axis(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            tree.split(p2, "y")

            assert tree.up(p2) is p1

        def test_motion_along_axis_in_nested_level(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "x")
            p4 = tree.split(p3, "y")

            assert tree.up(p4) is p3

        def test_motion_against_axis(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "x")

            assert tree.up(p3, wrap=False) is p1

        def test_motion_against_axis_in_nested_level(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "x")
            p4 = tree.split(p3, "y")
            p5 = tree.split(p4, "x")

            assert tree.up(p5) is p3

        def test_when_wrap_is_true_and_pane_is_at_edge_of_screen_then_pane_from_other_edge_of_screen_is_returned(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p2, "y")

            assert tree.up(p1, wrap=True) is p3

        def test_when_wrap_is_true_and_pane_is_its_own_sibling_then_the_pane_itself_is_returned(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            tree.split(p2, "y")

            assert tree.up(p1, wrap=True) is p1

        def test_when_wrap_is_false_and_pane_is_at_edge_of_screen_then_the_pane_itself_is_returned(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            tree.split(p2, "y")

            assert tree.up(p1, wrap=False) is p1

        def test_when_there_are_multiple_adjacent_panes_then_the_most_recently_focused_one_is_chosen(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            p3 = tree.split(p1, "x")
            p4 = tree.split(p3, "x")
            p5 = tree.split(p4, "x")
            tree.focus(p5)
            tree.focus(p3)
            tree.focus(p4)

            assert tree.up(p2) is p4

        def test_non_adjacent_panes_further_away_in_the_requested_direction_are_not_considered(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y", 1 - (Pane.min_size * 2))
            p3 = tree.split(p2, "y")

            tree.focus(p2)
            assert tree.up(p3) is p2
            tree.focus(p1)
            assert tree.up(p3) is p2

        def test_adjacent_panes_that_only_partly_share_borders_are_candidates(self):
            tree = Tree()
            p1 = tree.add_tab()
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
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
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
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "y")
            p3 = tree.add_tab(p1, new_level=True)
            p4 = tree.add_tab(p3)
            tree.focus(p4)

            assert tree.up(p2) is p4

        def test_deeply_nested_adjacent_panes_in_different_super_containers(self):
            tree = Tree()
            p1 = tree.add_tab()
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
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.add_tab(p1)
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
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.add_tab(p2, new_level=True)
            p4 = tree.split(p3, "y")
            tree.focus(p4)

            p = tree.next_tab(p2)

            assert p is p4

        def test_when_a_node_is_provided_that_is_not_under_a_tc_then_an_error_is_raised(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            tree.add_tab()

            _, _, tc = p1.get_ancestors()

            err_msg = "The provided node is not under a `TabContainer` node"
            with pytest.raises(ValueError, match=err_msg):
                tree.next_tab(tc)

        def test_wrap_is_respected(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.add_tab(p1)

            p = tree.next_tab(p2, wrap=True)
            assert p is p1

            p = tree.next_tab(p2, wrap=False)
            assert p is None

    class TestPrev:
        def test_when_any_node_is_provided_then_mru_pane_in_prev_tab_of_nearest_tc_is_returned(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.add_tab(p1)
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
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.split(p1, "x")
            p3 = tree.add_tab(p2, new_level=True)
            p4 = tree.split(p2, "y")
            tree.focus(p4)

            p = tree.prev_tab(p3)

            assert p is p4

        def test_when_a_node_is_provided_that_is_not_under_a_tc_then_an_error_is_raised(
            self,
        ):
            tree = Tree()
            p1 = tree.add_tab()
            tree.add_tab()

            _, _, tc = p1.get_ancestors()

            err_msg = "The provided node is not under a `TabContainer` node"
            with pytest.raises(ValueError, match=err_msg):
                tree.prev_tab(tc)

        def test_wrap_is_respected(self):
            tree = Tree()
            p1 = tree.add_tab()
            p2 = tree.add_tab(p1)

            p = tree.prev_tab(p1, wrap=True)
            assert p is p2

            p = tree.prev_tab(p1, wrap=False)
            assert p is None


class TestIterWalk:
    def test_new_tree_instance_has_no_nodes(self):
        tree = Tree()

        assert list(tree.iter_walk()) == []


class TestSubscribe:
    def test_returns_subscription_id(self):
        tree = Tree()
        callback = mock.Mock()

        subscription_id = tree.subscribe(TreeEvent.node_added, callback)

        assert isinstance(subscription_id, str)


class TestRepr:
    def test_empty_tree(self):
        tree = Tree()

        assert repr(tree) == "<empty>"
