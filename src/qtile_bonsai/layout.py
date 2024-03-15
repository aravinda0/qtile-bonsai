# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


import ast
import collections
import dataclasses
import enum
import itertools
import os
import pathlib
import re
import tempfile
from datetime import datetime
from typing import Any, Callable, ClassVar, Sequence

from libqtile.backend.base.window import Window
from libqtile.command.base import expose_command
from libqtile.config import ScreenRect
from libqtile.layout.base import Layout
from libqtile.log_utils import logger

import qtile_bonsai.validation as validation
from qtile_bonsai.core.geometry import DirectionParam
from qtile_bonsai.core.tree import (
    Axis,
    Pane,
    SplitContainer,
    SupernodeTarget,
    Tab,
    Tree,
    TreeEvent,
)
from qtile_bonsai.theme import Gruvbox
from qtile_bonsai.tree import BonsaiNodeMixin, BonsaiPane, BonsaiTree
from qtile_bonsai.utils.process import modify_terminal_cmd_with_cwd


@dataclasses.dataclass
class LayoutOption:
    name: str
    default_value: Any
    description: str
    validator: Callable[[str, Any], tuple[bool, str | None]] | None = None

    # This is just a documentation helper. To allow us to present enum values such as
    # `Gruvbox.bright_red` as the friendly enum string instead of a cryptic `#fb4934`.
    default_value_label: str | None = None


class Bonsai(Layout):
    class AddClientMode(enum.Enum):
        initial_restoration_check = 1
        restoration_in_progress = 2
        normal = 3

    level_specific_config_format = re.compile(r"^L(\d+)\.(.+)")

    # Analogous to qtile's `Layout.defaults`, but has some more handy metadata.
    # `Layout.defaults` is set below, derived from this.
    options: ClassVar[list[LayoutOption]] = [
        LayoutOption(
            "window.margin",
            0,
            """
            Size of the margin space around windows. 
            Can be an int or a list of ints in [top, right, bottom, left] ordering.
            """,
        ),
        LayoutOption(
            "window.border_size",
            1,
            """
            Width of the border around windows. Must be a single integer value since
            that's what qtile allows for window borders.
            """,
            validator=validation.validate_border_size,
        ),
        LayoutOption(
            "window.border_color",
            Gruvbox.darker_yellow,
            "Color of the border around windows",
            default_value_label="Gruvbox.darker_yellow",
        ),
        LayoutOption(
            "window.active.border_color",
            Gruvbox.dark_yellow,
            "Color of the border around an active window",
            default_value_label="Gruvbox.dark_yellow",
        ),
        LayoutOption(
            "window.normalize_on_remove",
            True,
            """
            Whether or not to normalize the remaining windows after a window is removed.
            If `True`, the remaining sibling windows will all become of equal size.
            If `False`, the next (right/down) window will take up the free space.
            """,
        ),
        LayoutOption(
            "tab_bar.height",
            20,
            "Height of tab bars",
        ),
        LayoutOption(
            "tab_bar.hide_when",
            "single_tab",
            """
            When to hide the tab bar. Allowed values are 'never', 'always',
            'single_tab'.

            When 'single_tab' is configured, the bar is not shown whenever there is a
            lone tab remaining, but shows up again when another tab is added. 

            For nested tab levels, configuring 'always' or 'single_tab' actually means
            that when only a single tab remains, its contents get 'merged' upwards,
            eliminating the sub-tab level.
            """,
        ),
        LayoutOption(
            "tab_bar.margin",
            0,
            """
            Size of the margin space around tab bars.

            Can be an int or a list of ints in [top, right, bottom, left] ordering.
            """,
        ),
        LayoutOption(
            "tab_bar.border_size",
            0,
            "Size of the border around tab bars",
            validator=validation.validate_border_size,
        ),
        LayoutOption(
            "tab_bar.border_color",
            Gruvbox.dark_yellow,
            "Color of border around tab bars",
            default_value_label="Gruvbox.dark_yellow",
        ),
        LayoutOption(
            "tab_bar.bg_color",
            Gruvbox.bg0,
            "Background color of tab bars, beind their tabs",
            default_value_label="Gruvbox.bg0",
        ),
        LayoutOption(
            "tab_bar.tab.min_width", 50, "Minimum width of a tab on a tab bar"
        ),
        LayoutOption(
            "tab_bar.tab.margin", 0, "Size of the margin space around individual tabs"
        ),
        LayoutOption(
            "tab_bar.tab.padding",
            20,
            "Size of the padding space inside individual tabs",
        ),
        LayoutOption(
            "tab_bar.tab.bg_color",
            Gruvbox.bg1,
            "Background color of individual tabs",
            default_value_label="Gruvbox.bg1",
        ),
        LayoutOption(
            "tab_bar.tab.fg_color",
            Gruvbox.fg1,
            "Foreground text color of individual tabs",
            default_value_label="Gruvbox.fg1",
        ),
        LayoutOption(
            "tab_bar.tab.font_family", "Mono", "Font family to use for tab titles"
        ),
        LayoutOption("tab_bar.tab.font_size", 15, "Font size to use for tab titles"),
        LayoutOption(
            "tab_bar.tab.active.bg_color",
            Gruvbox.bg4,
            "Background color of active tabs",
            default_value_label="Gruvbox.bg4",
        ),
        LayoutOption(
            "tab_bar.tab.active.fg_color",
            Gruvbox.fg1,
            "Foreground text color of the active tab",
            default_value_label="Gruvbox.fg1",
        ),
        LayoutOption(
            "restore.threshold_seconds",
            4,
            """
            You likely don't need to tweak this. 
            Controls the time within which a persisted state file is considered to be
            from a recent qtile config-reload/restart event. If the persisted file is
            this many seconds old, we restore our window tree from it.
            """,
        ),
    ]
    defaults: ClassVar[list[tuple[str, Any, str]]] = [
        (option.name, option.default_value, option.description) for option in options
    ]

    def __init__(self, **config) -> None:
        super().__init__(**config)
        self.add_defaults(self.defaults)

        # We declare everything here, but things are initialized in `self._init()`. See
        # docs for `self.clone()`.
        self._tree: Tree
        self._focused_window: Window | None
        self._windows_to_panes: dict[Window, BonsaiPane]
        self._on_next_window: Callable[[], BonsaiPane]

        self._add_client_mode: Bonsai.AddClientMode = (
            self.AddClientMode.initial_restoration_check
        )
        self._restoration_window_id_to_pane_id: dict[int, int] = {}

    @property
    def focused_window(self) -> Window | None:
        return self._focused_window

    @property
    def focused_pane(self) -> Pane | None:
        if self.focused_window is not None:
            return self._windows_to_panes[self.focused_window]
        return None

    def clone(self, group):
        """In the manner qtile expects, creates a fresh, blank-slate instance of this
        class.

        This is a bit different from traditional copying/cloning of any 'current' state
        of the layout instance. In qtile, the config file holds the 'first' instance of
        the layout. Then, as each `Group` is created, it is initialized with 'clones' of
        that original instance.

        All the qtile-provided built-in layouts perform a state-resetting in their
        `clone()` implementations.

        So in practice, it seems qtile treats `Layout.clone()` sort of like an 'init'
        function.
        Here, we lean into this fully. We can instantiate a `Bonsai` layout instance,
        but we can only use it after `_init()` is called, which happens via `clone()`
        when qtile is ready to provide us with the associated `Group` instance.
        """
        pseudo_clone = super().clone(group)
        pseudo_clone._init()
        return pseudo_clone

    def layout(self, windows: Sequence[Window], screen_rect: ScreenRect):
        """Handles window layout based on the internal tree representation.

        Unlike the base class implementation, this does not invoke `Layout.configure()`
        for each window, as there are other elements such as tab-bar panels to process
        as well.
        """
        self._sync_with_screen_rect(screen_rect)
        self._tree.render(screen_rect)

    def configure(self, window: Window, screen_rect: ScreenRect):
        """Defined since this is an abstract method, but not implemented since things
        are handled in `self.layout()`.
        """
        raise NotImplementedError

    def add_client(self, window: Window):
        """Register a newly added window with this layout.

        This is usually straightforward, but we do some funky things here to support
        restoration of state after a qtile 'reload config'/'restart' event.

        In qtile-bonsai, the end user completely controls window positioning. It's not
        predictable the way most of qtile's built-in formulatic layouts are.
        So when qtile is reloaded after config changes, or restarted entirely, we would
        normally lose all the positioning information, since qtile will destroy the
        layout instance and create it anew post-reload/restart.

        We work around this by saving the layout state to a file just before reload
        happens. Then, post-reload, we read back the file to try and restore the layout
        state.

        Now, post-reload, qtile creates the layout instance again. Then it uses its
        usual window-creation flow and passes each existing window to the layout
        one-by-one as if new windows were being created in rapid succession.

        We have to hook into this 're-addition of windows' flow to perform our
        restoration. Note that this has to work over multiple steps, each time when
        qtile calls `Layout.add_client()`.

        To see if a reload/restart event happened recently, we look at the timestamp
        saved in our state file. If the state file exists at all and the timestamp is
        within a few seconds, it's safe enough in practice to assume that a
        reload/restart happened just recently.

        In summary, `add_client()` goes through a bit of state machine magic. The states
        are specified in `Bonsai.AddClientMode`.
        """
        if self._add_client_mode == Bonsai.AddClientMode.initial_restoration_check:
            pane = self._handle_add_client__initial_restoration_check(window)
        elif self._add_client_mode == Bonsai.AddClientMode.restoration_in_progress:
            pane = self._handle_add_client__restoration_in_progress(window)
        else:
            pane = self._handle_add_client__normal(window)

        pane.window = window
        self._windows_to_panes[window] = pane

    def remove(self, window: Window) -> Window | None:
        pane = self._windows_to_panes[window]
        normalize_on_remove = self._tree.get_config(
            "window.normalize_on_remove", level=pane.tab_level
        )

        _, _, next_focus_pane = self._tree.remove(pane, normalize=normalize_on_remove)
        del self._windows_to_panes[window]

        # Set to None immediately so as not to use stale references in the time between
        # remove() and the next focus() invocation. eg. float/unfloat
        self._focused_window = None

        if next_focus_pane is not None:
            return next_focus_pane.window

        return None

    def focus(self, window: Window):
        self._focused_window = window
        self._tree.focus(self.focused_pane)

    def focus_first(self) -> Window | None:
        first = next(self._tree.iter_panes(), None)
        if first is not None:
            return first.window
        return None

    def focus_last(self) -> Window | None:
        panes = list(self._tree.iter_panes())
        if panes:
            return panes[-1].window
        return None

    def focus_next(self, window) -> Window | None:
        current_pane = self._windows_to_panes[window]
        panes = list(self._tree.iter_panes())
        i = panes.index(current_pane)
        if i != len(panes) - 1:
            return panes[i + 1].window
        return None

    def next(self, window) -> Window | None:
        return self.focus_next(window)

    def focus_previous(self, window) -> Window | None:
        current_pane = self._windows_to_panes[window]
        panes = list(self._tree.iter_panes())
        i = panes.index(current_pane)
        if i != 0:
            return panes[i - 1].window
        return None

    def previous(self, window) -> Window | None:
        return self.previous(window)

    def hide(self):
        # While other layouts are active, ensure that any new windows are captured
        # consistenty with the default tab layout here.
        self._on_next_window = self._handle_default_next_window

        self._tree.hide()

    def finalize(self):
        self._persist_tree_state()
        self._tree.finalize()

    @expose_command
    def spawn_split(
        self,
        program: str,
        axis: Axis,
        *,
        ratio: float = 0.5,
        normalize: bool = True,
        auto_cwd_for_terminals: bool = True,
    ):
        """
        Launch the provided `program` into a new window that splits the currently
        focused window along the specified `axis`.

        Args:
            `program`:
                The program to launch.
            `axis`:
                The axis along which to split the currently focused window. Can be 'x'
                or 'y'.
                An `x` split will end up with two top/bottom windows.
                A `y` split will end up with two left/right windows.
            `ratio`:
                The ratio of sizes by which to split the current window.
                If a window has a width of 100, then splitting on the y-axis with a
                ratio = 0.3 will result in a left window of width 30 and a right window
                of width 70.
                Defaults to 0.5.
            `normalize`:
                If `True`, overrides `ratio` and leads to the new window and all sibling
                windows becoming of equal size along the corresponding split axis.
                Defaults to `True`.
            `auto_cwd_for_terminals`:
                (Experimental).
                If `True`, and the provided `program` is a well known terminal emulator,
                will try to open the new terminal window in the current working
                directory.

        Examples:
            - layout.spawn_split(my_terminal, "x")
            - layout.spawn_split(my_terminal, "y", ratio=0.2, normalize=False)
        """
        if self._tree.is_empty:
            logger.warn("There are no windows yet to split")
            return

        def _handle_next_window():
            target = self.focused_pane or self._tree.find_mru_pane()
            return self._tree.split(target, axis, ratio=ratio, normalize=normalize)

        self._on_next_window = _handle_next_window

        self._spawn_program(program, auto_cwd_for_terminals)

    @expose_command
    def spawn_tab(
        self,
        program: str,
        *,
        new_level: bool = False,
        level: int | None = None,
        auto_cwd_for_terminals: bool = True,
    ):
        """
        Launch the provided `program` into a new window as a new tab.

        Args:
            `program`:
                The program to launch.
            `new_level`:
                If `True`, create a new sub-tab level with 2 tabs. The first sub-tab
                being the currently focused window, the second sub-tab being the newly
                launched program.
            `level`:
                If provided, launch the new window as a tab at the provided `level` of
                tabs in the currently focused window's tab hierarchy.
                Level 1 is the topmost level.
            `auto_cwd_for_terminals`:
                See docs under `spawn_split()`

        Examples:
            - layout.spawn_tab(my_terminal)
            - layout.spawn_tab(my_terminal, new_level=True)
            - layout.spawn_tab("qutebrowser", level=1)
        """
        # We use this closed-over flag to ensure that after the explicit user-invoked
        # spawning of a tab based on the provided variables, any subsequent 'implicit'
        # tabs that are spawned are done so in a sensible manner. eg. if user invokes a
        # new subtab, any subsequent implicitly created tabs should not create further
        # subtabs since they were not explicitly asked for.
        fall_back_to_default_tab_spawning = False

        def _handle_next_window():
            nonlocal fall_back_to_default_tab_spawning

            if not fall_back_to_default_tab_spawning:
                fall_back_to_default_tab_spawning = True
                return self._tree.tab(
                    self.focused_pane, new_level=new_level, level=level
                )

            # Subsequent implicitly created tabs are spawned at whatever level
            # `self.focused_pane` is in.
            return self._tree.tab(self.focused_pane)

        self._on_next_window = _handle_next_window

        self._spawn_program(program, auto_cwd_for_terminals)

    @expose_command
    def left(self, *, wrap: bool = True):
        """
        Move focus to the window left of the currently focused window. If there are
        multiple candidates, the most recently focused of them will be chosen.

        Args:
            `wrap`:
                If `True`, will wrap around the edge and select windows from the right
                end of the screen.
                Defaults to `True`.
        """
        if self._tree.is_empty:
            return

        next_pane = self._tree.left(self.focused_pane, wrap=wrap)
        self._request_focus(next_pane)

    @expose_command
    def right(self, *, wrap: bool = True):
        """
        Same as `left()`, but moves focus to the right side.
        """
        if self._tree.is_empty:
            return

        next_pane = self._tree.right(self.focused_pane, wrap=wrap)
        self._request_focus(next_pane)

    @expose_command
    def up(self, *, wrap: bool = True):
        """
        Same as `left()`, but moves focus upwards.
        """
        if self._tree.is_empty:
            return

        next_pane = self._tree.up(self.focused_pane, wrap=wrap)
        self._request_focus(next_pane)

    @expose_command
    def down(self, *, wrap: bool = True):
        """
        Same as `left()`, but moves focus downwards.
        """
        if self._tree.is_empty:
            return

        next_pane = self._tree.down(self.focused_pane, wrap=wrap)
        self._request_focus(next_pane)

    @expose_command
    def next_tab(self, *, wrap: bool = True):
        """
        Switch focus to the next tab. The window that was previously active there will
        be focused.

        Args:
            `wrap`:
                If `True`, will cycle back to the fist tab if invoked on the last tab.
                Defaults to `True`.
        """
        if self._tree.is_empty:
            return

        next_pane = self._tree.next_tab(self.focused_pane, wrap=wrap)
        if next_pane is not None:
            self._request_focus(next_pane)

    @expose_command
    def prev_tab(self, *, wrap: bool = True):
        """
        Same as `next_tab()` but switches focus to the previous tab.
        """
        if self._tree.is_empty:
            return

        next_pane = self._tree.prev_tab(self.focused_pane, wrap=wrap)
        if next_pane is not None:
            self._request_focus(next_pane)

    @expose_command
    def resize_left(self, amount: int = 10):
        """
        Resizes by moving an appropriate vertical border leftwards. Usually this is the
        right border, but for the 'last' window under a SplitContainer, it will be the
        left border.

        Basically the way tmux does resize.

        If there are multiple nested windows under the area being resized, those windows
        are resized proportionally.

        Args:
            `amount`:
                The amount by which to resize.

        Examples:
            - layout.resize_left(30)
        """
        if self._tree.is_empty:
            return

        self._tree.resize(self.focused_pane, Axis.x, -amount)
        self._request_relayout()

    @expose_command
    def resize_right(self, amount: int = 10):
        """
        Same as `resize_right()` but moves a border rightwards.
        """
        if self._tree.is_empty:
            return

        self._tree.resize(self.focused_pane, Axis.x, amount)
        self._request_relayout()

    @expose_command
    def resize_up(self, amount: int = 10):
        """
        Same as `resize_right()` but moves a border upwards.
        """
        if self._tree.is_empty:
            return

        self._tree.resize(self.focused_pane, Axis.y, -amount)
        self._request_relayout()

    @expose_command
    def resize_down(self, amount: int = 10):
        """
        Same as `resize_right()` but moves a border downwards.
        """
        if self._tree.is_empty:
            return

        self._tree.resize(self.focused_pane, Axis.y, amount)
        self._request_relayout()

    @expose_command
    def swap_left(self, *, wrap: bool = False):
        """
        Swaps the currently focused window with the window to the left. If there are
        multiple candidates to pick from on the left, then the most recently focused one
        is chosen.

        Args:
            `wrap`:
                If `True`, will wrap around the edge and select windows from the right
                end of the screen to swap.
                Defaults to `False`.
        """
        if self._tree.is_empty:
            return

        other_pane = self._tree.left(self.focused_pane, wrap=wrap)
        if other_pane is self.focused_pane:
            return

        self._tree.swap(self.focused_pane, other_pane)
        self._request_relayout()

    @expose_command
    def swap_right(self, *, wrap: bool = False):
        """
        Same as `swap_left()` but swaps with a right neighbor.
        """
        if self._tree.is_empty:
            return

        other_pane = self._tree.right(self.focused_pane, wrap=wrap)
        if other_pane is self.focused_pane:
            return

        self._tree.swap(self.focused_pane, other_pane)
        self._request_relayout()

    @expose_command
    def swap_up(self, *, wrap: bool = False):
        """
        Same as `swap_left()` but swaps with an upwards neighbor.
        """
        if self._tree.is_empty:
            return

        other_pane = self._tree.up(self.focused_pane, wrap=wrap)
        if other_pane is self.focused_pane:
            return

        self._tree.swap(self.focused_pane, other_pane)
        self._request_relayout()

    @expose_command
    def swap_down(self, *, wrap: bool = False):
        """
        Same as `swap_left()` but swaps with a downwards neighbor.
        """
        if self._tree.is_empty:
            return

        other_pane = self._tree.down(self.focused_pane, wrap=wrap)
        if other_pane is self.focused_pane:
            return

        self._tree.swap(self.focused_pane, other_pane)
        self._request_relayout()

    @expose_command
    def swap_prev_tab(self, *, wrap: bool = True):
        """
        Swaps the currently active tab with the previous tab.

        Args:
            `wrap`:
                If `True`, will wrap around the edge of the tab bar and swap with the
                last tab.
                Defaults to `True`.
        """
        if self._tree.is_empty:
            return

        current_tab = self.focused_pane.get_first_ancestor(Tab)
        other_tab = current_tab.sibling(-1, wrap=wrap)

        if current_tab is not other_tab and other_tab is not None:
            self._tree.swap_tabs(current_tab, other_tab)
            self._request_relayout()

    @expose_command
    def swap_next_tab(self, *, wrap: bool = True):
        """
        Same as `swap_prev_tab()` but swap with the next tab.
        """
        if self._tree.is_empty:
            return

        current_tab = self.focused_pane.get_first_ancestor(Tab)
        other_tab = current_tab.sibling(1, wrap=wrap)

        if current_tab is not other_tab and other_tab is not None:
            self._tree.swap_tabs(current_tab, other_tab)
            self._request_relayout()

    @expose_command
    def rename_tab(self, widget: str = "prompt"):
        """
        Rename the currently active tab.

        Args:
            `widget`:
                The qtile widget that should be used for obtaining user input for the
                renaming. The 'prompt' widget is used by default.
        """
        prompt_widget = self.group.qtile.widgets_map.get(widget)
        if prompt_widget is None:
            logger.error(f"The '{widget}' widget was not found")
            return

        prompt_widget.start_input("Rename tab: ", self._handle_rename_tab)

    @expose_command
    def merge_to_subtab(
        self,
        direction: DirectionParam,
        *,
        src_target: SupernodeTarget = SupernodeTarget.mru_subtab_else_deepest,
        dest_target: SupernodeTarget = SupernodeTarget.mru_subtab_else_deepest,
        normalize: bool = True,
    ):
        """Merge the currently focused window (or an ancestor node) with a neighboring
        node in the specified `direction`, so that they both come under a (possibly new)
        subtab.

        Args:
            `direction`:
                The direction in which to find a neighbor to merge with.
            `src_target`:
                Determines how the source window/node should be resolved. ie. do we pick
                just the current window, or all windows under an appropriate ancestor
                container.
                Valid values are defined in `SupernodeTarget`. See below.
            `dest_target`:
                Determines how the neighboring node should be resolved, similar to how
                `src_target` is resolved.
                Valid values are defined in `SupernodeTarget`. See below.
            `normalize`:
                If `True`, any removals during the merge process will ensure all sibling
                nodes are resized to be of equal dimensions.

        Valid values for `SupernodeTarget` are:
            `"mru_deepest"`:
                Pick a single innermost window. If there are multiple such neighboring
                windows, pick the most recently used (MRU) one.
            `"mru_subtab_else_deepest"` (default):
                If the target is under a subtab, pick the subtab. If there is no subtab
                in play, behaves like `mru_deepest`.
            `"mru_largest"`
                Given a window, pick the largest ancestor node that the window's border
                is a fragment of. This resolves to a SplitContainer or a TabContainer.
            `"mru_subtab_else_largest"`
                If the target is under a subtab, pick the subtab. If there is no subtab
                in play, behaves like `mru_largest`.
        """
        if self._tree.is_empty:
            return

        self._tree.merge_with_neighbor_to_subtab(
            self.focused_pane,
            direction,
            src_target=src_target,
            dest_target=dest_target,
            normalize=normalize,
        )
        self._request_relayout()

    @expose_command
    def normalize(self, *, recurse: bool = True):
        """
        Starting from the focused window's SplitContainer, make all windows in the
        container of equal size.

        Args:
            `recurse`:
                If `True`, then nested nodes are also normalized similarly.
        """
        if self._tree.is_empty:
            return

        sc, *_ = self.focused_pane.get_ancestors(SplitContainer)
        self._tree.normalize(sc, recurse=recurse)
        self._request_relayout()

    @expose_command
    def normalize_tab(self, *, recurse: bool = True):
        """
        Starting from the focused window's tab, make all windows in the tab of equal
        size.

        Args:
            `recurse`:
                If `True`, then nested nodes are also normalized similarly.
                Defaults to `True`.
        """
        if self._tree.is_empty:
            return

        tab, *_ = self.focused_pane.get_ancestors(Tab)
        self._tree.normalize(tab, recurse=recurse)
        self._request_relayout()

    @expose_command
    def normalize_all(self):
        """
        Make all windows under all tabs be of equal size.
        """
        if self._tree.is_empty:
            return

        self._tree.normalize(self._tree.root, recurse=True)
        self._request_relayout()

    @expose_command
    def info(self):
        return {
            "name": "bonsai",
            "tree": repr(self._tree),
        }

    def _handle_default_next_window(self) -> BonsaiPane:
        return self._tree.tab()

    def _init(self):
        config = self.parse_multi_level_config()

        # We initialize the tree with arbitrary dimensions. These get reset soon as this
        # layout's group is assigned to a screen.
        self._tree = BonsaiTree(100, 100, config=config)
        self._tree.validate_config()

        self._tree.subscribe(
            TreeEvent.node_added, lambda nodes: self._handle_added_tree_nodes(nodes)
        )
        self._tree.subscribe(
            TreeEvent.node_removed, lambda nodes: self._handle_removed_tree_nodes(nodes)
        )

        self._focused_window = None
        self._windows_to_panes = {}

        def _handle_next_window():
            return self._tree.tab()

        self._on_next_window = _handle_next_window

    def parse_multi_level_config(self) -> BonsaiTree.MultiLevelConfig:
        options_map = {option.name: option for option in self.options}
        merged_user_config = itertools.chain(
            ((option.name, option.default_value) for option in self.options),
            ((k, v) for k, v in self._user_config.items()),
        )

        multi_level_config: BonsaiTree.MultiLevelConfig = collections.defaultdict(dict)
        for key, value in merged_user_config:
            level_specific_key = self.level_specific_config_format.match(key)
            level = 0
            if level_specific_key is not None:
                level = int(level_specific_key.group(1))
                key = level_specific_key.group(2)

            option = options_map.get(key)
            if option is not None and option.validator is not None:
                is_valid, err_msg = option.validator(key, value)
                if not is_valid:
                    logger.error(
                        f"{err_msg} "
                        f"Falling back to default value of {option.default_value}"
                    )
                    value = option.default_value

            multi_level_config[level][key] = value

        return multi_level_config

    def _sync_with_screen_rect(self, screen_rect: ScreenRect):
        w_changed = screen_rect.width != self._tree.width
        h_changed = screen_rect.height != self._tree.height
        if w_changed or h_changed:
            self._tree.reset_dimensions(screen_rect.width, screen_rect.height)

    def _handle_added_tree_nodes(self, nodes: list[BonsaiNodeMixin]):
        for node in nodes:
            node.init_ui(self.group.qtile)

    def _handle_removed_tree_nodes(self, nodes: list[BonsaiNodeMixin]):
        for node in nodes:
            node.finalize()

    def _handle_rename_tab(self, new_title: str):
        tab = self.focused_pane.get_first_ancestor(Tab)
        tab.title = new_title
        self._request_relayout()

    def _request_focus(self, pane: BonsaiPane):
        self.group.focus(pane.window)

    def _request_relayout(self):
        self.group.layout_all()

    def _spawn_program(self, program: str, auto_cwd_for_terminals: bool):
        if auto_cwd_for_terminals and self.focused_window is not None:
            program = modify_terminal_cmd_with_cwd(
                program, self.focused_window.get_pid()
            )

        self.group.qtile.spawn(program)

    def _persist_tree_state(self):
        if self._tree.is_empty:
            return

        state = {
            "timestamp": datetime.now().isoformat(),
            "focus_wid": self.focused_window.wid,
            "tree": self._tree.as_dict(),
        }

        state_file_path = self._get_state_file_path(self.group)
        state_file_path.parent.mkdir(exist_ok=True, parents=True)
        state_file_path.write_text(repr(state))

    def _handle_add_client__initial_restoration_check(self, window) -> BonsaiPane:
        persisted_state = self._check_for_persisted_state()
        if persisted_state is not None:
            logger.info("Found persisted state. Attempting restoration...")

            persisted_tree = persisted_state["tree"]
            self._tree.reset(from_state=persisted_tree)
            self._windows_to_panes.clear()
            self._restoration_window_id_to_pane_id = (
                self._get_windows_to_panes_mapping_from_state(persisted_tree)
            )

            self._add_client_mode = Bonsai.AddClientMode.restoration_in_progress

            # Invoke the in-progress handler once to handle the current window.
            return self._handle_add_client__restoration_in_progress(window)

        self._add_client_mode = Bonsai.AddClientMode.normal
        return self._handle_add_client__normal(window)

    def _handle_add_client__restoration_in_progress(self, window: Window) -> BonsaiPane:
        pane_id = self._restoration_window_id_to_pane_id.get(window.wid)
        if pane_id is not None:
            pane = next((p for p in self._tree.iter_panes() if p.id == pane_id), None)
            del self._restoration_window_id_to_pane_id[window.wid]

            if not self._restoration_window_id_to_pane_id:
                # We've restored all windows. Change to normal mode.
                self._add_client_mode = Bonsai.AddClientMode.normal

                logger.info("Restoration from persisted state complete.")
        else:
            logger.warning(
                f"While trying to restore from state, received a window with "
                f"wid={window.wid} that wasn't part of the persisted state."
            )

            # We shouldn't ever end up here, but in case we do, pass the window on to
            # the normal handler so it's still handled.
            pane = self._handle_add_client__normal(window)

        return pane

    def _handle_add_client__normal(self, window: Window) -> BonsaiPane:
        if self._tree.is_empty:
            self._on_next_window = self._handle_default_next_window

        return self._on_next_window()

    def _get_windows_to_panes_mapping_from_state(self, state: dict) -> dict:
        windows_to_panes = {}

        def walk(n):
            if n["type"] == BonsaiPane.abbrv():
                windows_to_panes[n["wid"]] = n["id"]
            else:
                for c in n["children"]:
                    walk(c)

        walk(state["root"])

        return windows_to_panes

    def _check_for_persisted_state(self) -> dict | None:
        state_file = self._get_state_file_path(self.group)
        if state_file.is_file():
            try:
                state = ast.literal_eval(state_file.read_text())
                persist_timestamp = datetime.fromisoformat(state["timestamp"])
                seconds_since_persist = (datetime.now() - persist_timestamp).seconds
                restore_threshold_seconds = self._tree.get_config(
                    "restore.threshold_seconds"
                )
                if seconds_since_persist <= restore_threshold_seconds:
                    return state

                logger.info(
                    "Found a state file, but not performing restore since it's stale."
                )
            except Exception:
                logger.error(
                    "Could not read state file. Proceeding without state restoration.",
                )
                return None

            logger.info("Deleting state file.")
            state_file.unlink()
        return None

    def _get_state_file_path(self, group) -> pathlib.Path:
        tmp_dir = tempfile.gettempdir()
        return pathlib.Path(f"{tmp_dir}/qtile_bonsai/state_{os.getpid()}_{group.name}")
