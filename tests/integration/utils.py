from libqtile import bar, config, layout

from qtile_bonsai import Bonsai, BonsaiBar
from tests.integration.conftest import TestConfigBase, test_display_resolution, wait


def make_config_with_bar(widget_config: dict | None = None):
    widget_config = widget_config or {}

    class BonsaiBarTestConfig(TestConfigBase):
        layouts = [Bonsai(), layout.Columns(num_columns=3)]
        screens = [config.Screen(bottom=bar.Bar([BonsaiBar(**widget_config)], 50))]

    return BonsaiBarTestConfig()


def make_config_with_bar_and_multiple_screens(
    layout_config: dict | None = None, widget_config: dict | None = None
):
    layout_config = layout_config or {}
    widget_config = widget_config or {}

    class BonsaiBarMultiScreenTestConfig(TestConfigBase):
        layouts = [Bonsai(**layout_config)]

        # 💢 can't seem to get regular `screens` config to work. `manager.get_screens()`
        # only ever shows the one screen. Wondered if it was something to do with how
        # pyvirtualdisplay is set up, but same behavior under wayland tests...
        # `fake_screens` seems to work though...
        fake_screens = [
            config.Screen(
                bottom=bar.Bar([BonsaiBar(**widget_config)], 50),
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
