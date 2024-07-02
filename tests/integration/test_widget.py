# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

import pytest
from libqtile import bar, config, layout

from qtile_bonsai import Bonsai, BonsaiBar
from tests.integration.conftest import TestConfigBase, wait


def make_config_with_bar(**bonsai_bar_config):
    class BonsaiBarTestConfig(TestConfigBase):
        layouts = [Bonsai(), layout.Columns(num_columns=3)]
        screens = [config.Screen(bottom=bar.Bar([BonsaiBar(**bonsai_bar_config)], 50))]

    return BonsaiBarTestConfig()


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
