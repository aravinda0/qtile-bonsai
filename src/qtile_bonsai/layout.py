# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


import ast
import collections
import enum
import itertools
import os
import pathlib
import re
import tempfile
from datetime import datetime
from typing import Callable, ClassVar

from libqtile.backend.base.window import Window
from libqtile.command.base import expose_command
from libqtile.config import ScreenRect
from libqtile.layout.base import Layout
from libqtile.log_utils import logger

from qtile_bonsai.core.tree import Axis, Pane, SplitContainer, Tab, Tree, TreeEvent
from qtile_bonsai.theme import Gruvbox
from qtile_bonsai.tree import BonsaiNodeMixin, BonsaiPane, BonsaiTree
from qtile_bonsai.utils.process import modify_terminal_cmd_with_cwd


class Bonsai(Layout):
    class AddClientMode(enum.Enum):
        initial_restoration_check = 1
        restoration_in_progress = 2
        normal = 3

    level_specific_config_format = re.compile(r"^L(\d+)\.(.+)")
    defaults: ClassVar = [
        (
            "window.margin",
            0,
            """
            Size of the margin space around windows.
            Can be an int or a list of ints in [top, right, bottom, left] ordering.
            """,
        ),
        (
            "window.border_size",
            1,
            "Width of the border around windows",
        ),
        (
            "window.border_color",
            Gruvbox.darker_yellow,
            "Color of the border around windows",
        ),
        (
            "window.active.border_color",
            Gruvbox.dark_yellow,
            "Color of the border around an active window",
        ),
        (
            "window.normalize_on_remove",
            True,
            """
            Whether or not to normalize the remaining windows after a window is removed.
            If `True`, the remaining windows will all become of equal size.
            If `False`, the next (right/down) window will take up the free space.
            """,
        ),
        (
            "tab_bar.height",
            20,
            "Height of tab bars",
        ),
        (
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
        (
            "tab_bar.margin",
            0,
            """
            Size of the margin space around tab bars.
            Can be an int or a list of ints in [top, right, bottom, left] ordering.
            """,
        ),
        (
            "tab_bar.border_size",
            0,
            "Size of the border around tab bars",
        ),
        (
            "tab_bar.border_color",
            Gruvbox.dark_yellow,
            "Color of border around tab bars",
        ),
        (
            "tab_bar.bg_color",
            Gruvbox.bg0,
            "Background color of tab bars, beind their tabs",
        ),
        ("tab_bar.tab.min_width", 50, "Minimum width of a tab on a tab bar"),
        ("tab_bar.tab.margin", 0, "Size of the margin space around individual tabs"),
        ("tab_bar.tab.padding", 20, "Size of the padding space inside individual tabs"),
        (
            "tab_bar.tab.bg_color",
            Gruvbox.bg1,
            "Background color of individual tabs",
        ),
        (
            "tab_bar.tab.fg_color",
            Gruvbox.fg1,
            "Foreground text color of individual tabs",
        ),
        ("tab_bar.tab.font_family", "Mono", "Font family to use for tab titles"),
        ("tab_bar.tab.font_size", 15, "Font size to use for tab titles"),
        (
            "tab_bar.tab.active.bg_color",
            Gruvbox.bg4,
            "Background color of active tabs",
        ),
        (
            "tab_bar.tab.active.fg_color",
            Gruvbox.fg1,
            "Foreground text color of the active tab",
        ),
        (
            "restore.threshold_seconds",
            4,
            """
            You likely don't need to tweak this. Controls the time within which a
            persisted state file is considered to be from a recent qtile
            config-reload/restart event. If the persisted file is this many seconds old,
            we restore our window tree from it.
            """,
        ),
    ]

    def __init__(self, **config) -> None:
        super().__init__(**config)
        self.add_defaults(self.defaults)

        self._tree: Tree
        self._focused_window: Window | None
        self._windows_to_panes: dict[Window, BonsaiPane]
        self._on_next_window: Callable[[], BonsaiPane]

        self._add_client_mode: Bonsai.AddClientMode = (
            self.AddClientMode.initial_restoration_check
        )
        self._restoration_window_id_to_pane_id: dict[int, int] = {}

        self._reset()

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
        the layout, then each Group instance 'clones' of that original instance (which
        likely remains in its initial state) and uses the new instance for all future
        operations.

        All the built-in layouts perform a state-resetting in their `clone()`
        implementations.

        So in practice, qtile treats the `Layout.clone()` method more like a factory
        method, to create fresh instances.
        """
        pseudo_clone = super().clone(group)
        pseudo_clone._reset()
        return pseudo_clone

    def layout(self, windows: list[Window], screen_rect: ScreenRect):
        """Handles window layout based on the internal tree representation.

        Unlike the base class implementation, this does not invoke `Layout.configure()`
        for each window, as there are other elements such as tab-bar panels to process
        as well.
        """
        for node in self._tree.iter_walk():
            if self._tree.is_visible(node):
                node.render(screen_rect, self._tree)
            else:
                node.hide()

    def configure(self, window: Window, screen_rect: ScreenRect):
        """Defined since this is an abstract method, but not implemented since things
        are handled in `self.layout()`.
        """
        raise NotImplementedError

    def add_client(self, window: Window):
        """Register a newly added window in the context of this layout.

        This is usually straightforward, but we do some funky things here to support
        restoration of state after a qtile 'reload config' event or a 'restart' event.

        qtile-bonsai is a stateless layout - the end user controls the positioning of
        windows. So when qtile is reloaded after config changes, or restarted entirely,
        we would normally lose all the positioning information, since qtile will destroy
        the layout instance and create it anew post-reload/restart.

        We work around this by saving the layout state to a file just before reload
        happens. Then, post-reload, we read back the file to try and restore the layout
        state.

        Now, post-reload, qtile creates the layout instance again. Then it uses its
        usual window-creation flow and passes each existing window to the layout
        one-by-one as if new windows were being created in rapid succession. So our
        restoration has to work over multiple steps, each time qtile calls
        `Layout.add_client()`.

        As an aside, since there is no 'reload' or 'restart' hook in qtile, and since we
        have no other non-layout place to put our code, we also have to do the initial
        'restoration check' here in this method. To see if a reload/restart event
        happened recently by looking at the timestamp saved in our state file.
        If the state file exists at all and the timestamp is within a few seconds, it's
        safe enough in practice to assume that a reload/restart happened just recently.

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
        next_focus_pane = self._tree.remove(pane, normalize=normalize_on_remove)
        del self._windows_to_panes[window]
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

    def show(self, screen_rect: ScreenRect):
        width_changed = screen_rect.width != self._tree.width
        height_changed = screen_rect.height != self._tree.height
        if width_changed or height_changed:
            self._tree.reset_dimensions(screen_rect.width, screen_rect.height)

    def hide(self):
        # While other layouts are active, ensure that any new windows are captured
        # consistenty with the default tab layout here.
        self._on_next_window = self._handle_default_next_window

        self._hide_all_internal_windows()

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
        if self._tree.is_empty:
            logger.warn("There are no windows yet to split")
            return

        def _handle_next_window():
            return self._tree.split(
                self.focused_pane, axis, ratio=ratio, normalize=normalize
            )

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
        if self._tree.is_empty:
            return

        next_pane = self._tree.left(self.focused_pane, wrap=wrap)
        self._request_focus(next_pane)

    @expose_command
    def right(self, *, wrap: bool = True):
        if self._tree.is_empty:
            return

        next_pane = self._tree.right(self.focused_pane, wrap=wrap)
        self._request_focus(next_pane)

    @expose_command
    def up(self, *, wrap: bool = True):
        if self._tree.is_empty:
            return

        next_pane = self._tree.up(self.focused_pane, wrap=wrap)
        self._request_focus(next_pane)

    @expose_command
    def down(self, *, wrap: bool = True):
        if self._tree.is_empty:
            return

        next_pane = self._tree.down(self.focused_pane, wrap=wrap)
        self._request_focus(next_pane)

    @expose_command
    def next_tab(self, *, wrap: bool = True):
        if self._tree.is_empty:
            return

        next_pane = self._tree.next_tab(self.focused_pane, wrap=wrap)
        if next_pane is not None:
            self._request_focus(next_pane)

    @expose_command
    def prev_tab(self, *, wrap: bool = True):
        if self._tree.is_empty:
            return

        next_pane = self._tree.prev_tab(self.focused_pane, wrap=wrap)
        if next_pane is not None:
            self._request_focus(next_pane)

    @expose_command
    def resize_left(self, amount: int = 10):
        if self._tree.is_empty:
            return

        self._tree.resize(self.focused_pane, Axis.x, -amount)
        self._request_relayout()

    @expose_command
    def resize_right(self, amount: int = 10):
        if self._tree.is_empty:
            return

        self._tree.resize(self.focused_pane, Axis.x, amount)
        self._request_relayout()

    @expose_command
    def resize_up(self, amount: int = 10):
        if self._tree.is_empty:
            return

        self._tree.resize(self.focused_pane, Axis.y, -amount)
        self._request_relayout()

    @expose_command
    def resize_down(self, amount: int = 10):
        if self._tree.is_empty:
            return

        self._tree.resize(self.focused_pane, Axis.y, amount)
        self._request_relayout()

    @expose_command
    def swap_up(self, *, wrap: bool = False):
        if self._tree.is_empty:
            return

        other_pane = self._tree.up(self.focused_pane, wrap=wrap)
        if other_pane is self.focused_pane:
            return

        self._tree.swap(self.focused_pane, other_pane)
        self._request_relayout()

    @expose_command
    def swap_down(self, *, wrap: bool = False):
        if self._tree.is_empty:
            return

        other_pane = self._tree.down(self.focused_pane, wrap=wrap)
        if other_pane is self.focused_pane:
            return

        self._tree.swap(self.focused_pane, other_pane)
        self._request_relayout()

    @expose_command
    def swap_left(self, *, wrap: bool = False):
        if self._tree.is_empty:
            return

        other_pane = self._tree.left(self.focused_pane, wrap=wrap)
        if other_pane is self.focused_pane:
            return

        self._tree.swap(self.focused_pane, other_pane)
        self._request_relayout()

    @expose_command
    def swap_right(self, *, wrap: bool = False):
        if self._tree.is_empty:
            return

        other_pane = self._tree.right(self.focused_pane, wrap=wrap)
        if other_pane is self.focused_pane:
            return

        self._tree.swap(self.focused_pane, other_pane)
        self._request_relayout()

    @expose_command
    def swap_prev_tab(self, *, wrap: bool = True):
        if self._tree.is_empty:
            return

        current_tab = self.focused_pane.get_first_ancestor(Tab)
        other_tab = current_tab.sibling(-1, wrap=wrap)

        if current_tab is not other_tab and other_tab is not None:
            self._tree.swap_tabs(current_tab, other_tab)
            self._request_relayout()

    @expose_command
    def swap_next_tab(self, *, wrap: bool = True):
        if self._tree.is_empty:
            return

        current_tab = self.focused_pane.get_first_ancestor(Tab)
        other_tab = current_tab.sibling(1, wrap=wrap)

        if current_tab is not other_tab and other_tab is not None:
            self._tree.swap_tabs(current_tab, other_tab)
            self._request_relayout()

    @expose_command
    def rename_tab(self, widget: str = "prompt"):
        prompt_widget = self.group.qtile.widgets_map.get(widget)
        if prompt_widget is None:
            logger.error(f"The '{widget}' widget was not found")
            return

        prompt_widget.start_input("Rename tab: ", self._handle_rename_tab)

    @expose_command
    def normalize(self, *, recurse: bool = True):
        """Starting from the focused pane's container, will make all panes in the
        container of equal size.

        If `recurse` is `True`, then nested nodes are also normalized similarly.
        """
        if self._tree.is_empty:
            return

        sc, *_ = self.focused_pane.get_ancestors(SplitContainer)
        self._tree.normalize(sc, recurse=recurse)
        self._request_relayout()

    @expose_command
    def normalize_tab(self, *, recurse: bool = True):
        """Starting from the focused pane's tab, will make all panes in the
        tab of equal size.

        If `recurse` is `True`, then nested nodes are also normalized similarly.
        """
        if self._tree.is_empty:
            return

        tab, *_ = self.focused_pane.get_ancestors(Tab)
        self._tree.normalize(tab, recurse=recurse)
        self._request_relayout()

    @expose_command
    def normalize_all(self):
        """Makes all windows under all tabs be of equal size."""
        if self._tree.is_empty:
            return

        self._tree.normalize(self._tree.root, recurse=True)
        self._request_relayout()

    @expose_command
    def info(self):
        return {
            "name": "bonsai",
            "tree": str(self._tree),
        }

    def _handle_default_next_window(self) -> BonsaiPane:
        return self._tree.tab()

    def _reset(self):
        # We initialize the tree with arbitrary dimensions. These get reset soon as this
        # layout's group is assigned to a screen.
        self._tree = BonsaiTree(100, 100, config=self.parse_multi_level_config())

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
        merged_user_config = itertools.chain(
            ((c[0], c[1]) for c in self.defaults),
            ((k, v) for k, v in self._user_config.items()),
        )

        multi_level_config: BonsaiTree.MultiLevelConfig = collections.defaultdict(dict)
        for key, value in merged_user_config:
            level_specific_key = self.level_specific_config_format.match(key)
            level = 0
            if level_specific_key is not None:
                level = int(level_specific_key.group(1))
                key = level_specific_key.group(2)
            multi_level_config[level][key] = value

        return multi_level_config

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

    def _hide_all_internal_windows(self):
        for node in self._tree.iter_walk():
            node.hide()

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
