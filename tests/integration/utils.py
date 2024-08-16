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
