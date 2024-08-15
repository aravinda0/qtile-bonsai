# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

import pytest
from libqtile import bar, config, layout

from qtile_bonsai import Bonsai, BonsaiBar
from tests.integration.conftest import TestConfigBase, test_display_resolution, wait


def make_config_with_bar(**bonsai_bar_config):
    class BonsaiBarTestConfig(TestConfigBase):
        layouts = [Bonsai(), layout.Columns(num_columns=3)]
        screens = [config.Screen(bottom=bar.Bar([BonsaiBar(**bonsai_bar_config)], 50))]

    return BonsaiBarTestConfig()


def make_config_with_bar_and_multiple_screen(**bonsai_bar_config):
    class BonsaiBarMultiScreenTestConfig(TestConfigBase):
        layouts = [Bonsai()]

        # 💢 can't seem to get regular `screens` config to work. `manager.get_screens()`
        # only ever shows the one screen. Wondered if it was something to do with how
        # pyvirtualdisplay is set up, but same behavior under wayland tests...
        # `fake_screens` seems to work though...
        fake_screens = [
            config.Screen(
                bottom=bar.Bar([BonsaiBar(**bonsai_bar_config)], 50),
                x=0,
                y=0,
                width=test_display_resolution[0],
                height=test_display_resolution[1] // 2,
            ),
            config.Screen(
                x=0,
                y=test_display_resolution[1],
                width=test_display_resolution[0],
                height=test_display_resolution[1] // 2,
            ),
        ]

    return BonsaiBarMultiScreenTestConfig()


@pytest.mark.parametrize(
    "qtile_config",
    [
        make_config_with_bar(
            **{
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
                make_config_with_bar_and_multiple_screen(
                    **{
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
                make_config_with_bar_and_multiple_screen(
                    **{
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
