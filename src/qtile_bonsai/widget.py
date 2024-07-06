# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


# Disable private usage checks. qtile has some unconventionally named base classes.
# Disable @override labelling - since that's only available on python 3.12.
# pyright: reportPrivateUsage=false, reportImplicitOverride=false


from typing import Any, ClassVar

from libqtile import hook
from libqtile.backend.base.drawer import Drawer, TextLayout
from libqtile.widget import base

from qtile_bonsai.core.geometry import Box, Rect
from qtile_bonsai.layout import Bonsai
from qtile_bonsai.theme import Gruvbox
from qtile_bonsai.utils.config import ConfigOption


class BonsaiBar(base._Widget):
    """A widget that can behave like a tab bar for the Bonsai layout and displays all
    top level tabs.

    A handy way to use this is to configure the Bonsai layout with

    `Bonsai(**{"L1.tab_bar.hide_when": "always"})`

    so that only the top level tab bar is hidden at the layout level, and use this
    qtile-bar widget instead.
    """

    default_length = 500

    options: ClassVar[list[ConfigOption]] = [
        ConfigOption(
            "length",
            default_length,
            """The standard `length` property of qtile widgets.""",
        ),
        ConfigOption(
            "bg_color",
            None,
            """
            Background color of the bar. 
            If None, the qtile-bar's' background color is used.
            """,
        ),
        ConfigOption("font_family", "Mono", "Font family to use for tab titles"),
        ConfigOption("font_size", 15, "Size of the font to use for tab titles"),
        ConfigOption("tab.width", 50, "Width of a tab on a tab bar."),
        ConfigOption(
            "tab.margin",
            0,
            "Size of the space on either outer side of individual tabs.",
        ),
        ConfigOption(
            "tab.padding",
            0,
            "Size of the space on either inner side of individual tabs.",
        ),
        ConfigOption(
            "tab.bg_color",
            Gruvbox.dull_yellow,
            "Background color of the inactive tabs",
            default_value_label="Gruvbox.dull_yellow",
        ),
        ConfigOption(
            "tab.fg_color",
            Gruvbox.fg1,
            "Foreground color of the inactive tabs",
            default_value_label="Gruvbox.fg1",
        ),
        ConfigOption(
            "tab.active.bg_color",
            Gruvbox.vivid_yellow,
            "Background color of active tab",
            default_value_label="Gruvbox.vivid_yellow",
        ),
        ConfigOption(
            "tab.active.fg_color",
            Gruvbox.bg0_hard,
            "Foreground color of active tab",
            default_value_label="Gruvbox.bg0_hard",
        ),
        ConfigOption(
            "container_select_mode.indicator.bg_color",
            Gruvbox.dark_purple,
            "Background color of active tab when in container_select_mode.",
            default_value_label="Gruvbox.bg0_hard",
        ),
        ConfigOption(
            "container_select_mode.indicator.fg_color",
            Gruvbox.fg1,
            "Foreground color of active tab when in container_select_mode.",
            default_value_label="Gruvbox.bg0_hard",
        ),
    ]
    defaults: ClassVar[list[tuple[str, Any, str]]] = [
        (option.name, option.default_value, option.description) for option in options
    ]

    def __init__(self, length=default_length, **config):
        super().__init__(length, **config)
        self.add_defaults(self.defaults)

        self.text_layout: TextLayout | None = None

        # Just some annotations. Defined in base.
        self.drawer: Drawer

    @property
    def is_bonsai_active(self) -> bool:
        return isinstance(self.qtile.current_group.layout, Bonsai)

    def draw(self):
        self.drawer.clear(self.bg_color or self.bar.background)

        if self.is_bonsai_active:
            self._draw_when_bonsai_active()
        else:
            self._draw_when_bonsai_inactive()

        self.drawer.draw(
            offsetx=self.offsetx,
            offsety=self.offsety,
            width=self.width,
            height=self.height,
        )

    def finalize(self):
        self._remove_hooks()

        self.text_layout.finalize()

    def button_press(self, x: int, y: int, button: int):
        if not self.is_bonsai_active:
            return

        bonsai = self.qtile.current_group.layout
        root = bonsai.info()["tree"]["root"]
        if root is None:
            return

        tab_width: int = getattr(self, "tab.width")
        tab_margin: int = getattr(self, "tab.margin")

        # (x, y) are conveniently in object-space.
        i = x // tab_width
        if i > len(root["children"]) - 1:
            return

        tab_box = Box(
            principal_rect=Rect((i * tab_width), 0, tab_width, self.bar.size),
            margin=tab_margin,
        )
        if tab_box.border_rect.has_coord(x, y):
            bonsai.focus_nth_tab(i + 1, level=1)

    def _configure(self, qtile, bar):
        super()._configure(qtile, bar)

        # Make text layout with some dummy initials. Actuals set later.
        self.text_layout = self.drawer.textlayout("", "000000", "mono", 15, None)

        self._setup_hooks()

    def _setup_hooks(self):
        hook.subscribe.client_focus(self._handle_client_focus)

    def _remove_hooks(self):
        hook.unsubscribe.client_focus(self._handle_client_focus)

    def _handle_client_focus(self, client):
        self.draw()

    def _draw_when_bonsai_active(self):
        bonsai = self.qtile.current_group.layout
        bonsai_info = bonsai.info()
        root = bonsai_info["tree"]["root"]
        if root is None:
            return

        # TODO: make vertical compatible
        tab_width: int = getattr(self, "tab.width")
        tab_margin: int = getattr(self, "tab.margin")
        tab_padding: int = getattr(self, "tab.padding")
        font_family: str = getattr(self, "font_family")
        font_size: int = getattr(self, "font_size")
        is_container_select_mode = (
            bonsai_info["interaction_mode"]
            == Bonsai.InteractionMode.container_select.name
        )

        one_char_w, _ = self.drawer.max_layout_size(["x"], font_family, font_size)
        per_tab_max_chars = int(
            (tab_width - tab_margin * 2 - tab_padding * 2) / one_char_w
        )
        for i, n in enumerate(root["children"]):
            if n["id"] == root["active_child"]:
                if is_container_select_mode:
                    bg: str = getattr(self, "container_select_mode.indicator.bg_color")
                    fg: str = getattr(self, "container_select_mode.indicator.fg_color")
                else:
                    bg = getattr(self, "tab.active.bg_color")
                    fg = getattr(self, "tab.active.fg_color")
            else:
                bg = getattr(self, "tab.bg_color")
                fg = getattr(self, "tab.fg_color")

            self.drawer.set_source_rgb(bg)
            self.text_layout.colour = fg
            self.text_layout.font_family = font_family
            self.text_layout.font_size = font_size

            tab_box = Box(
                principal_rect=Rect((i * tab_width), 0, tab_width, self.bar.size),
                margin=tab_margin,
                border=0,
                padding=tab_padding,
            )
            self.drawer.fillrect(
                tab_box.border_rect.x,
                tab_box.border_rect.y,
                tab_box.border_rect.w,
                tab_box.border_rect.h,
            )

            # Truncate title based on available width
            tab_title = n["title_resolved"]
            if len(tab_title) > per_tab_max_chars:
                tab_title = f"{tab_title[:per_tab_max_chars - 1]}…"
            self.text_layout.text = tab_title

            # Center title text in the tab
            text_w, text_h = self.drawer.max_layout_size(
                [tab_title], font_family, font_size
            )
            text_offset_x = (tab_box.content_rect.w - text_w) / 2
            text_offset_y = (tab_box.content_rect.h - text_h) / 2

            self.text_layout.draw(
                tab_box.content_rect.x + text_offset_x,
                tab_box.content_rect.y + text_offset_y,
            )

    def _draw_when_bonsai_inactive(self):
        pass
