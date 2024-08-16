# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

import pytest

from tests.integration.conftest import wait
from tests.integration.utils import (
    make_config_with_bar,
    make_config_with_bar_and_multiple_screens,
)


@pytest.mark.parametrize(
    "qtile_config",
    [
        make_config_with_bar(
            widget_config={
                "tab.width": 50,
            }
        )
    ],
    indirect=True,
)
def test_when_widget_tab_clicked_then_that_tab_is_activated_in_layout(
    qtile_config, manager, spawn_test_window_cmd
):
    manager.layout.spawn_tab(spawn_test_window_cmd())
    wait()

    manager.layout.spawn_tab(spawn_test_window_cmd())
    wait()

    manager.layout.spawn_tab(spawn_test_window_cmd())
    wait()

    _, win2, win3 = manager.windows()

    assert manager.window.info()["id"] == win3["id"]

    second_tab_offset = 50

    # position arg is silliness. qtile says will drop it.
    manager.bar["bottom"].fake_button_press(
        screen=0, position="bottom", x=second_tab_offset, y=0
    )

    assert manager.window.info()["id"] == win2["id"]


class TestConfig:
    class TestSyncWith:
        @pytest.mark.parametrize(
            "qtile_config",
            [
                make_config_with_bar_and_multiple_screens(
                    widget_config={
                        "sync_with": "bonsai_on_same_screen",
                        "tab.width": 50,
                    }
                )
            ],
            indirect=True,
        )
        def test_when_value_is_bonsai_on_same_screen_then_widget_is_tied_to_bonsai_on_widget_screen(
            self, qtile_config, manager, make_window
        ):
            manager.to_screen(0)
            make_window()

            manager.to_screen(1)
            make_window()
            make_window()

            # We are focused on the 2nd screen and the 4th overall window.
            # The bar should still be displaying info of the layout on the 1st screen.
            assert (
                len(
                    manager.widget["bonsaibar"].info()["target_bonsai"]["tree"]["root"][
                        "children"
                    ]
                )
                == 1
            )

            # No changes expected when we switch back to the 1st screen.
            manager.to_screen(1)
            assert (
                len(
                    manager.widget["bonsaibar"].info()["target_bonsai"]["tree"]["root"][
                        "children"
                    ]
                )
                == 1
            )

        @pytest.mark.parametrize(
            "qtile_config",
            [
                make_config_with_bar_and_multiple_screens(
                    widget_config={
                        "sync_with": "bonsai_with_focus",
                        "tab.width": 50,
                    }
                )
            ],
            indirect=True,
        )
        def test_when_value_is_bonsai_with_focus_then_widget_syncs_with_any_bonsai_that_has_focus(
            self, qtile_config, manager, make_window
        ):
            manager.to_screen(0)
            make_window()

            manager.to_screen(1)
            make_window()
            make_window()

            # We are focused on the 2nd screen and the 4th overall window.
            # The bar should be displaying info of the Bonsai layout of the 2nd screen
            # soon as we switched to it.
            assert (
                len(
                    manager.widget["bonsaibar"].info()["target_bonsai"]["tree"]["root"][
                        "children"
                    ]
                )
                == 2
            )

            # We switch to the 1st screen. The bar should now be sync'd with the layout
            # active on the 1st screen.
            manager.to_screen(0)
            assert (
                len(
                    manager.widget["bonsaibar"].info()["target_bonsai"]["tree"]["root"][
                        "children"
                    ]
                )
                == 1
            )
