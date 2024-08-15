# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


# Disable private usage checks. qtile has some unconventionally named base classes.
# Disable @override labelling - since that's only available on python 3.12.
# pyright: reportPrivateUsage=false, reportImplicitOverride=false


from typing import Any, ClassVar

from libqtile import bar, hook
from libqtile.backend.base.drawer import Drawer, TextLayout
from libqtile.command.base import expose_command
from libqtile.widget import base

from qtile_bonsai.core.geometry import Box, Perimeter, Rect
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
            """
            The standard `length` property of qtile widgets.

            As usual, it can be a fixed integer, or one of the 'special' bar constants:
            `bar.CALCULATED` or `bar.STRETCH`.
            """,
        ),
        ConfigOption(
            "sync_with",
            "bonsai_on_same_screen",
            """
            The Bonsai layout whose state should be rendered on this widget.

            Can be one of the following:
                - `bonsai_with_focus`:
                    The Bonsai layout of the window that is currently focused. This is
                    relevant in a multi-screen setup - the widget will keep updating
                    based on which screen's Bonsai layout has focus.
                - `bonsai_on_same_screen`:
                    The widget will stick to displaying the state of the Bonsai layout
                    that is on the same screen as the widget's bar.
            """,
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
        ConfigOption(
            "tab.width",
            50,
            """
            Width of a tab on the bar. 

            Can be an int or `auto`. If `auto`, the tabs take up as much of the
            available space on the bar as possible.

            Note that if the `length` option is set to `bar.CALCULATED`, then you cannot
            provide `auto` here, as we would need fixed tab width values to perform the
            `bar.CALCULATED` computation.

            Note that this width follows the 'margin box'/'principal box' model, so it
            includes any configured margin amount.
            """,
        ),
        ConfigOption(
            "tab.margin",
            0,
            """
            Size of the space on either outer side of individual tabs.
            Can be an int or a list of ints in [top, right, bottom, left] ordering.
            """,
        ),
        ConfigOption(
            "tab.padding",
            0,
            """
            Size of the space on either inner side of individual tabs.
            Can be an int or a list of ints in [top, right, bottom, left] ordering.
            """,
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
        self._last_width: int = 0

        self.text_layout: TextLayout | None = None

        # Just some annotations. Defined in base.
        self.drawer: Drawer

    @property
    def target_bonsai(self) -> Bonsai | None:
        if self.sync_with == "bonsai_on_same_screen":
            active_layout = self.bar.screen.group.layout
        else:
            active_layout = self.qtile.current_group.layout

        if isinstance(active_layout, Bonsai):
            return active_layout

        return None

    @expose_command
    def info(self) -> dict:
        info = super().info()
        if self.target_bonsai is not None:
            info["target_bonsai"] = self.target_bonsai.info()
        else:
            info["target_bonsai"] = None
        return info

    def draw(self):
        width = self.width

        if self._should_redraw_whole_bar_instead():
            self._last_width = width
            self.bar.draw()
            return

        self.drawer.clear(self.bg_color or self.bar.background)

        if self.target_bonsai is not None:
            self._draw_when_bonsai_active()
        else:
            self._draw_when_bonsai_inactive()

        self.drawer.draw(
            offsetx=self.offsetx,
            offsety=self.offsety,
            width=width,
            height=self.height,
        )
        self._last_width = width

    def finalize(self):
        self._remove_hooks()

        self.text_layout.finalize()

    def button_press(self, x: int, y: int, button: int):
        if self.target_bonsai is None:
            return

        bonsai = self.target_bonsai
        root = bonsai.info()["tree"]["root"]
        if root is None:
            return

        tab_width: int = self._get_per_tab_width(root)
        tab_margin = Perimeter(getattr(self, "tab.margin"))

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

    def calculate_length(self) -> int:
        """Mandatory override for `Widget.calculate_length` to handle special values for
        `widget.length`.

        Notes:
            - `self.length` seems to delegate to this - but only when it is set to
                `bar.CALCULATED`.
                - For `bar.STATIC`, the original configured fixed length is simply
                returned.
                - For `bar.STRETCH`, the length is set at some point by the bar, and
                that length gets used instead, without coming here.
            - So for `bar.CALCULATED`, we need to calculate required space based on the
                `tab.width` config. `tab.width == 'auto'` cannot work in this case. We
                raise a config error in that situation anyway.
        """
        if not self.bar.horizontal:
            raise NotImplementedError(
                "This widget isn't yet supported on vertical bars."
            )

        tab_width_config = getattr(self, "tab.width")
        if self.length_type != bar.CALCULATED and tab_width_config == "auto":
            return self.length

        bonsai = self.target_bonsai
        if bonsai is None:
            return 0
        root = bonsai.info()["tree"]["root"]
        if root is None:
            return 0
        return min(tab_width_config * len(root["children"]), self.bar.width)

    def _configure(self, qtile, bar_instance):
        super()._configure(qtile, bar_instance)

        if self.length_type == bar.CALCULATED and getattr(self, "tab.width") == "auto":
            raise ValueError(
                "`tab.width` can't be 'auto' when widget length is `bar.CALCULATED"
            )

        # Make text layout with some dummy initials. Actuals set later.
        self.text_layout = self.drawer.textlayout("", "000000", "mono", 15, None)

        self._setup_hooks()

    def _setup_hooks(self):
        hook.subscribe.client_focus(self._handle_client_focus)
        hook.subscribe.client_killed(self._handle_client_killed)

    def _remove_hooks(self):
        hook.unsubscribe.client_killed(self._handle_client_killed)
        hook.unsubscribe.client_focus(self._handle_client_focus)

    def _should_redraw_whole_bar_instead(self) -> bool:
        if self.length_type == bar.CALCULATED and self._last_width != self.width:
            return True
        return False

    def _handle_client_focus(self, client):
        self.draw()

    def _handle_client_killed(self, client):
        # When the bar isn't static, we need to trigger a full bar re-render when no
        # windows are left.
        # Re-rendering the widget is primarily driven by the focus hook. But we're left
        # with an edge case of when there are no windows left, so we handle that here.
        bonsai = self.target_bonsai
        if (
            self.length_type != bar.STATIC
            and bonsai is not None
            and not bonsai.group.windows
        ):
            self.bar.draw()

    def _draw_when_bonsai_active(self):
        bonsai_info = self.target_bonsai.info()
        root = bonsai_info["tree"]["root"]
        if root is None:
            return

        # TODO: make vertical compatible
        tab_width: int = self._get_per_tab_width(root)
        tab_margin = Perimeter(getattr(self, "tab.margin"))
        tab_padding = Perimeter(getattr(self, "tab.padding"))
        font_family: str = self.font_family
        font_size: int = self.font_size
        is_container_select_mode = (
            bonsai_info["interaction_mode"]
            == Bonsai.InteractionMode.container_select.name
        )

        one_char_w, _ = self.drawer.max_layout_size(["x"], font_family, font_size)
        per_tab_max_chars = int(
            (
                tab_width
                - (tab_margin.left + tab_margin.right)
                - (tab_padding.left + tab_padding.right)
            )
            / one_char_w
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

    def _get_per_tab_width(self, tree_root) -> int:
        tab_width_config: int | str = getattr(self, "tab.width")

        if tab_width_config == "auto":
            return self.length // len(tree_root["children"])
        return int(tab_width_config)
