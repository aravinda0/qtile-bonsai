# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from __future__ import annotations

import collections
import textwrap
import uuid
from collections.abc import Iterable, Iterator
from typing import Any, Callable

from strenum import StrEnum

from qtile_bonsai.core.geometry import (
    Axis,
    AxisParam,
    Box,
    Direction,
    Direction1D,
    Direction1DParam,
    DirectionParam,
    PerimieterParams,
    Rect,
)
from qtile_bonsai.core.nodes import (
    Node,
    Pane,
    SplitContainer,
    Tab,
    TabBar,
    TabContainer,
)
from qtile_bonsai.core.utils import validate_unit_range


_PruningCase = collections.namedtuple("_PruningCase", ("chain", "prune"))


class TreeEvent(StrEnum):
    node_added = "node_added"
    node_removed = "node_removed"


_enum_type_mru_deepest = "mru_deepest"
_enum_type_mru_subtab_else_deepest = "mru_subtab_else_deepest"


class NodeHierarchySelectionMode(StrEnum):
    mru_deepest = _enum_type_mru_deepest
    mru_largest = "mru_largest"
    mru_subtab_else_deepest = _enum_type_mru_subtab_else_deepest
    mru_subtab_else_largest = "mru_subtab_else_largest"


class NodeHierarchyPullOutSelectionMode(StrEnum):
    mru_deepest = _enum_type_mru_deepest
    mru_subtab_else_deepest = _enum_type_mru_subtab_else_deepest


class InvalidTreeStructureError(Exception):
    pass


class InvalidNodeSelectionError(Exception):
    pass


class Tree:
    TreeEventCallback = Callable[[list[Node]], None]
    MultiLevelConfig = collections.defaultdict[int, dict[str, Any]]

    _recency_seq = 0

    # Tab levels of trees begin from 1 for the topmost level. Use 'level 0' to store
    # defaults.
    _default_config_level_key = 0

    def __init__(
        self,
        width: int,
        height: int,
        config: MultiLevelConfig | None = None,
    ):
        self._width: int = width
        self._height: int = height
        self._root: TabContainer | None = None

        self._config: Tree.MultiLevelConfig = self.make_default_config()
        if config is not None:
            for level, lconfig in config.items():
                for k, v in lconfig.items():
                    self._config[level][k] = v
            self.validate_config()

        self._event_subscribers: collections.defaultdict[
            TreeEvent, dict[str, Tree.TreeEventCallback]
        ] = collections.defaultdict(dict)
        self._pruning_cases = self._get_pruning_cases()

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def root(self) -> TabContainer | None:
        return self._root

    @property
    def is_empty(self) -> bool:
        return self.root is None

    def node(self, id: int) -> Node:
        """Return the node in the tree with the provided `id` or `None` if no such node
        exists.
        """
        for n in self.iter_walk():
            if n.id == id:
                return n
        raise ValueError(f"There is no node with the id: {id}")

    def make_default_config(self) -> collections.defaultdict[int, dict[str, Any]]:
        config = collections.defaultdict(dict)
        config[self._default_config_level_key] = {
            # The following are valid config that can be customized for the
            # single-pane-under-L1-tab scenario. They are not set by default since when
            # not set, we fall back to looking at the corresponding non-single window
            # config.
            # eg. `window.single.margin` is unset? => look at `window.margin`
            # ----------
            # "window.single.margin": 0,
            # "window.single.border_size": 1,
            # "window.single.padding": 0,
            # ----------
            "window.margin": 0,
            "window.border_size": 1,
            "window.padding": 0,
            "tab_bar.height": 20,
            "tab_bar.margin": 0,
            "tab_bar.border_size": 0,
            "tab_bar.padding": 0,
            "tab_bar.hide_when": "never",
        }
        return config

    def set_config(self, key: str, value: Any, *, level: int | None = None):
        level = level if level is not None else self._default_config_level_key
        if level < self._default_config_level_key:
            raise ValueError("`level` must be a positive number")

        self._config[level][key] = value

    def validate_config(self):
        """Validate config across config keys.

        Raises:
            `ValueError`: if there are any validation errors.
        """
        for level in self._config:
            self._validate_tab_bar_config(level)

    def get_config(
        self,
        key: str,
        *,
        level: int | None = None,
        fall_back_to_base_level: bool = True,
        default: Any = None,
    ) -> Any:
        level = level if level is not None else self._default_config_level_key
        if level < self._default_config_level_key:
            raise ValueError("`level` must be a positive number")

        if fall_back_to_base_level and (
            level not in self._config or key not in self._config[level]
        ):
            level = self._default_config_level_key

        if default is not None:
            return self._config[level].get(key, default)
        return self._config[level][key]

    def create_pane(
        self,
        principal_rect: Rect,
        *,
        margin: PerimieterParams | None = None,
        border: PerimieterParams | None = None,
        padding: PerimieterParams | None = None,
        tab_level: int | None = None,
    ) -> Pane:
        """Factory method for creating a new Pane instance.

        Passing `tab_level` allows us to apply appropriate level-based configuration to
        the pane.
        """

        if margin is None:
            margin = self.get_config("window.margin", level=tab_level)
        if border is None:
            border = self.get_config("window.border_size", level=tab_level)
        if padding is None:
            padding = self.get_config("window.padding", level=tab_level)

        return Pane(
            principal_rect=principal_rect,
            margin=margin,
            border=border,
            padding=padding,
        )

    def create_split_container(self) -> SplitContainer:
        """Factory method for creating a new SplitContainer instance"""
        return SplitContainer()

    def create_tab(self, title: str = "") -> Tab:
        """Factory method for creating a new Tab instance"""
        return Tab(title)

    def create_tab_container(self) -> TabContainer:
        """Factory method for creating a new TabContainer instance"""
        return TabContainer()

    def reset_dimensions(self, width: int, height: int):
        self._width = width
        self._height = height

        # Ensure the tree nodes get resized proportionally
        if self._root is not None:
            self._root.transform(Axis.x, 0, width)
            self._root.transform(Axis.y, 0, height)

    def tab(
        self,
        at_node: Node | None = None,
        *,
        new_level: bool = False,
        level: int | None = None,
    ) -> Pane:
        if self.is_empty:
            if at_node is not None or new_level or level is not None:
                raise ValueError(
                    "The tree is empty. The provided arguments are invalid."
                )

            tab, added_nodes = self._add_very_first_tab()
            pane = self.find_mru_pane(start_node=tab)
        elif new_level:
            if at_node is None:
                raise ValueError(
                    "`new_level` requires a reference `at_node` under which to add tabs"
                )

            tc, added_nodes = self._add_tab_at_new_level(at_node)
            pane = self.find_mru_pane(start_node=tc.children[-1])
        elif level is not None:
            if at_node is None:
                raise ValueError("`level` requires a reference `at_node`")
            if level < 1:
                raise ValueError("`level` must be 1 or higher")

            ancestor_tab_containers = at_node.get_ancestors(TabContainer)
            max_tab_level = len(ancestor_tab_containers)
            if level > max_tab_level:
                raise ValueError(
                    f"`{level}` is an invalid level. The tree currently only has "
                    f"{max_tab_level} levels."
                )

            tc = ancestor_tab_containers[-level]
            tab, added_nodes = self._add_tab(tc)
            pane = self.find_mru_pane(start_node=tab)
        else:
            if at_node is None:
                tc = self._root
            else:
                tc = at_node.get_first_ancestor(TabContainer)

            if tc is None:
                raise InvalidTreeStructureError

            tab, added_nodes = self._add_tab(tc)
            pane = self.find_mru_pane(start_node=tab)

        self._notify_subscribers(TreeEvent.node_added, added_nodes)

        return pane

    def split(
        self,
        node: Node,
        axis: AxisParam,
        *,
        ratio: float = 0.5,
        normalize: bool = False,
        position: Direction1DParam = Direction1D.next,
    ) -> Pane:
        """Create a new pane by splitting the provided `node` on the provided `axis`.

        If `normalize` is provided, it takes precedence over `ratio`. In this case, the
        new pane and all the sibling nodes will be adjusted to be of equal size.
        """
        axis = Axis(axis)
        position = Direction1D(position)

        new_p, added_nodes, removed_nodes = self._split(
            node, axis, ratio=ratio, normalize=normalize, position=position
        )
        self._notify_subscribers(TreeEvent.node_added, added_nodes)
        self._notify_subscribers(TreeEvent.node_removed, removed_nodes)

        return new_p

    def resize(self, pane: Pane, axis: AxisParam, amount: int):
        axis = Axis(axis)

        super_node = self._find_super_node_to_resize(pane, axis)
        if super_node is None:
            return

        if super_node.is_last_child:
            br1, br2 = super_node.operational_sibling, super_node
        else:
            br1, br2 = super_node, super_node.operational_sibling

        br_shrink = br2 if amount > 0 else br1
        actual_amount = min(abs(amount), br_shrink.shrinkability(axis))
        actual_amount = actual_amount if amount > 0 else -actual_amount

        points = [
            br1.principal_rect.coord(axis),
            br1.principal_rect.coord2(axis) + actual_amount,
            br2.principal_rect.coord2(axis),
        ]

        br1.transform(axis, points[0], points[1] - points[0])
        br2.transform(axis, points[1], points[2] - points[1])

    def normalize(self, node: Node | None = None, *, recurse: bool = True):
        def _normalize(node: Node, *, recurse: bool):
            if isinstance(node, SplitContainer):
                per_child_size = round(
                    node.principal_rect.size(node.axis) / len(node.children)
                )
                s = node.principal_rect.coord(node.axis)
                for child in node.children:
                    child.transform(node.axis, s, per_child_size)
                    s += per_child_size
            if recurse:
                for child in node.children:
                    _normalize(child, recurse=recurse)

        node = node or self.root
        _normalize(node, recurse=recurse)

    def remove(
        self, node: Node, *, normalize: bool = False
    ) -> tuple[Node, Node | None, Pane | None]:
        """Remove the provided `node` from the tree.

        Will also notify subscribers of `TreeEvent.node_removed` of all removed nodes.

        Args:
            `node`:
                The node to be removed. Note that the resolved removal point could also
                be an ancestor of this node.
            `normalize`:
                Whether removal should lead to all the `node` siblings to re-dimension
                themselves to take equal amounts of space.

        Returns:
            3-tuple:
                1. The `node` or an ancestor node that was the point of removal. This
                branch is now unlinked from the main tree.
                2. The sibling node of the removed node. Or `None` if no sibling exists.
                3. The next pane that ought to get focus. Usually the sibling of the
                removed node. But if the sibling is a Tab, then it is the MRU pane under
                the nearest TC.
        """
        rm_nodes = []
        next_focus_pane = None

        br_rm, _, br_sib, br_rm_nodes = self._remove(
            node, consume_vacant_space=True, normalize=normalize
        )
        if br_rm is self._root:
            self._root = None

        rm_nodes.extend(br_rm_nodes)
        if br_sib is not None:
            # Find an appropriate pane to focus next. When a tab is closed, it's nicer
            # to pick the MRU pane under the whole TC. eg. when we open some GUI
            # application as a far-away tab from the 'current' window, it's nicer UX to
            # return focus to the original window on closing it.
            # Otherwise, it's generally nicest to give focus to the sibling node.
            if isinstance(br_sib, Tab):
                active_tc = br_sib.get_first_ancestor(TabContainer)
                next_focus_pane = self.find_mru_pane(start_node=active_tc)
            else:
                next_focus_pane = self.find_mru_pane(start_node=br_sib)
            rm_nodes.extend(self._do_post_removal_pruning(br_sib))

        self._notify_subscribers(TreeEvent.node_removed, rm_nodes)

        return (br_rm, br_sib, next_focus_pane)

    def reset(self, from_state: dict | None = None):
        """Clear the current tree. If `from_state` is provided, restore state from
        there.

        Subscribers will be notified of nodes that are removed/added in the process.


        NOTE:
            For the moment, only the nodes and their `box.principal_rect` information is
            read from `from_state`. Things like margins/border/padding, tab bar
            settings, are read from the current config.
            This aligns with how we want things when working under qtile, which is our
            current scope.
            Later™, We can figure out how to make this more general (like simply restore
            as-is from provided state), while still working for qtile.
        """
        removed_nodes = list(self.iter_walk())
        self._root = None
        self._notify_subscribers(TreeEvent.node_removed, removed_nodes)

        if from_state is not None:
            self._root = self._parse_state(from_state)
            if self._root is not None:
                self.reevaluate_dynamic_attributes(self._root)
            added_nodes = list(self.iter_walk())
            self._notify_subscribers(TreeEvent.node_added, added_nodes)

    def focus(self, pane: Pane):
        """Ensures the provided `pane` is visible by activating all ancestor tabs.

        For the moment, we don't actually maintain the focused node internally, which
        aligns with usage alongside extrnal window managers that control the notion of
        focus.
        """
        node = pane
        while node.parent is not None:
            if isinstance(node, Tab):
                node.parent.active_child = node
            node = node.parent
        pane.recency = self.next_recency_value()

    def adjacent_node(
        self, node: Node, direction: DirectionParam, *, wrap: bool = True
    ) -> Node:
        """Return the node that is adjacent to the provided `node` in the specified
        direction. This may be a 'supernode' that is a container for multiple child
        nodes.
        Returns the node itself when there are no suitable sibling nodes.

        NOTES:
            - Tab bars are ignored. Two panes can be adjacent even if a subtab bar
              appears between them.
        """
        direction = Direction(direction)

        supernode = self.find_border_encompassing_supernode(node, direction)
        if supernode is None:
            return node

        supernode_sibling = supernode.sibling(direction.axis_unit, wrap=wrap)
        if supernode_sibling is None or supernode_sibling is supernode:
            return node

        return supernode_sibling

    def adjacent_pane(
        self, pane: Pane, direction: DirectionParam, *, wrap: bool = True
    ) -> Pane:
        """Returns the single MRU pane that is adjacent to the provided `node` in the
        specified direction.
        """
        adjacent = self.adjacent_panes(pane, direction, wrap=wrap)
        if not adjacent:
            return pane
        return self.find_mru_pane(panes=adjacent)

    def adjacent_panes(
        self, node: Node, direction: DirectionParam, *, wrap: bool = True
    ) -> list[Pane]:
        """Returns all panes that are adjacent to the provided `node` in the specified
        `direction`.
        """
        direction = Direction(direction)

        supernode_sibling = self.adjacent_node(node, direction, wrap=wrap)
        if supernode_sibling is node:
            return []

        adjacent = []
        inv_axis = direction.axis.inv
        for candidate in self._find_panes_along_border(supernode_sibling, direction):
            coord1_ok = candidate.principal_rect.coord(
                inv_axis
            ) < node.principal_rect.coord2(inv_axis)
            coord2_ok = candidate.principal_rect.coord2(
                inv_axis
            ) > node.principal_rect.coord(inv_axis)
            if coord1_ok and coord2_ok:
                adjacent.append(candidate)

        return adjacent

    def next_tab(
        self, node: Node, *, level: int = -1, wrap: bool = True
    ) -> Pane | None:
        return self._next_tab(node, 1, level=level, wrap=wrap)

    def prev_tab(
        self, node: Node, *, level: int = -1, wrap: bool = True
    ) -> Pane | None:
        return self._next_tab(node, -1, level=level, wrap=wrap)

    def swap(self, p1: Pane, p2: Pane):
        """Swaps the two panes provided in the tree."""
        sc1 = p1.parent
        p1_index = sc1.children.index(p1)

        sc2 = p2.parent
        p2_index = sc2.children.index(p2)

        p1.parent, p2.parent = p2.parent, p1.parent
        sc1.children[p1_index], sc2.children[p2_index] = (
            sc2.children[p2_index],
            sc1.children[p1_index],
        )

        # Swap geometries
        p1.box, p2.box = p2.box, p1.box

    def swap_tabs(self, t1: Tab, t2: Tab):
        """Swaps the two tabs provided in the tree and adjusts geometries as needed. The
        provided tabs must not be nested under one another.
        """
        if t1 in t2.get_ancestors() or t2 in t1.get_ancestors():
            raise ValueError(
                "`t1` and `t2` must be independent tabs such that one is not nested "
                "under the other"
            )

        tc1 = t1.parent
        t1_index = tc1.children.index(t1)
        t1_rect = Rect.from_rect(t1.principal_rect)

        tc2 = t2.parent
        t2_index = tc2.children.index(t2)
        t2_rect = Rect.from_rect(t2.principal_rect)

        t1.parent, t2.parent = t2.parent, t1.parent
        tc1.children[t1_index], tc2.children[t2_index] = (
            tc2.children[t2_index],
            tc1.children[t1_index],
        )

        if tc1 is not tc2:
            t1.transform(Axis.x, t2_rect.x, t2_rect.w)
            t1.transform(Axis.y, t2_rect.y, t2_rect.h)
            t2.transform(Axis.x, t1_rect.x, t1_rect.w)
            t2.transform(Axis.y, t1_rect.y, t1_rect.h)

    def merge_tabs(self, src: Tab, dest: Tab, axis: AxisParam):
        if not isinstance(src, Tab) or not isinstance(dest, Tab):
            raise ValueError("Both `src` and `dest` must be `Tab` instances")
        axis = Axis(axis)

        removed_nodes = []
        br_rm, _, br_sib, _removed_nodes = self._remove(src)
        removed_nodes.extend(_removed_nodes)
        if br_sib is not None:
            removed_nodes.extend(self._do_post_removal_pruning(br_sib))

        br_rm_sc = br_rm.children[0]
        dest_sc = dest.children[0]
        _, added_nodes, _removed_nodes = self._split(
            dest_sc, axis, insert_node=br_rm_sc
        )
        removed_nodes.extend(_removed_nodes)

        self._notify_subscribers(TreeEvent.node_added, added_nodes)
        self._notify_subscribers(TreeEvent.node_removed, removed_nodes)

    def merge_to_subtab(self, src: Node, dest: Node, *, normalize: bool = False):
        """Merge `src` and `dest` such that they both come under a (possibly new)
        TabContainer.

        Args:
            `src`:
                The source branch.
            `dest`:
                The target node where the merged branch will exist.
            `normalize`:
                Passed on to internal invocations of `remove()` to determine if siblings
                should be resized to be of equal dimensions.
        """
        # If we're provided a Pane target, respect that. Else find an appropriate
        # ancestor to resolve to.
        if not isinstance(dest, Pane):
            dest, _ = self._find_removal_branch(dest)
            if isinstance(dest, Tab):
                dest = dest.parent

        if src is dest:
            raise ValueError(
                "`src` and `dest` resolve to the same node. Cannot merge a node with "
                "itself."
            )
        if src in dest.get_ancestors() or dest in src.get_ancestors():
            raise ValueError(
                "The resolved nodes for `src` and `dest` cannot already be under "
                "one another."
            )

        added_nodes = []
        removed_nodes = []

        src, _, src_remnant_sibling, _ = self._remove(src, normalize=normalize)
        if src_remnant_sibling is not None:
            removed_nodes.extend(self._do_post_removal_pruning(src_remnant_sibling))

        # Grab rect only after invoking `_remove()`. In case space redistribution
        # happens, there may be cases where `dest` is affected. We want to capture those
        # updates before we shove `src` into `dest`.
        dest_rect = Rect.from_rect(dest.principal_rect)

        is_src_tc = isinstance(src, TabContainer)
        is_dest_tc = isinstance(dest, TabContainer)

        if is_src_tc and is_dest_tc:
            for t in src.children:
                self._add_tab(dest, insert_node=t, tc_rect=dest_rect)
            dest.active_child = src.active_child
            removed_nodes.append(src)
        elif is_src_tc:
            # Pluck out `dest`,
            dest_container = dest.parent
            dest_pos = dest_container.children.index(dest)
            dest_container.children.remove(dest)
            dest.parent = None

            # Put in `src` where `dest` used to be
            dest_container.children.insert(dest_pos, src)
            src.parent = dest_container
            src.transform(Axis.x, dest_rect.x, dest_rect.w)
            src.transform(Axis.y, dest_rect.y, dest_rect.h)

            # Shove `dest` under `src` as a new tab
            _, _added_nodes = self._add_tab(
                src, insert_node=dest, tc_rect=dest_rect, focus_new=False
            )
            added_nodes.extend(_added_nodes)
        elif is_dest_tc:
            # Shove `src` under `dest` as a new tab
            _, _added_nodes = self._add_tab(dest, insert_node=src, tc_rect=dest_rect)
            added_nodes.extend(_added_nodes)
        else:
            _, _added_nodes = self._add_tab_at_new_level(dest, insert_node=src)
            added_nodes.extend(_added_nodes)

        self._notify_subscribers(TreeEvent.node_removed, removed_nodes)
        self._notify_subscribers(TreeEvent.node_added, added_nodes)

    def merge_with_neighbor_to_subtab(
        self,
        node: Node,
        direction: DirectionParam,
        *,
        src_selection: NodeHierarchySelectionMode = NodeHierarchySelectionMode.mru_subtab_else_deepest,
        dest_selection: NodeHierarchySelectionMode = NodeHierarchySelectionMode.mru_subtab_else_deepest,
        normalize: bool = False,
    ):
        """Merge the provided `node` (or a resolved ancestor) with a geometrically
        neighboring node so that they both come under a (possibly new) TabContainer.

        Args:
            `node`:
                The node to merge with a neighbor.
            `direction`:
                The geometric direction in which to find a neighboring node to merge
                with.
            `src_selection`:
                Determines how `node` should be resolved.
            `dest_selection`:
                Determines how the neighboring node should be resolved.
            `normalize`:
                Passed on to internal invocations of `remove()` to determine if siblings
                should be resized to be of equal dimensions.
        """
        direction = Direction(direction)

        src = self.resolve_node_selection(node, src_selection, direction)
        dest = self.resolve_node_neighbor_selection(node, dest_selection, direction)

        self.merge_to_subtab(src, dest, normalize=normalize)

    def push_in(self, src: Node, dest: Node, *, normalize: bool = False):
        """Take `src` and insert it as a child under `dest`"""

        # Grab ancestors just in case needed for pruning edge case.
        dest_ancestors = dest.get_ancestors(SplitContainer)

        # Determine target axis. Important to do this before any possible pruning from
        # the upcoming `_remove()` which may leave dest with a new parent.
        dest_container = dest.get_self_or_first_ancestor(SplitContainer)
        axis = (
            dest_container.axis.inv
            if isinstance(dest, (Pane, TabContainer))
            else dest_container.axis
        )

        removed_nodes = []
        br_rm, _, br_sib, _ = self._remove(src, normalize=normalize)
        if br_sib is not None:
            removed_nodes.extend(self._do_post_removal_pruning(br_sib))

        # If we end up plucking out a T, just use the underlying SC
        if isinstance(br_rm, Tab):
            removed_nodes.append(br_rm)
            br_rm = br_rm.children[0]

        # After the `_remove()` and the pruning operation, check if `dest` happens to be
        # one of the pruned nodes. If so, reassign `dest` to be the closest valid
        # (non-pruned) SC ancestor.
        # NOTE: When `normalize == False`, this has a seemingly unnatural effect on
        # space distribution as we end up using a larger ancestor node's space for
        # reference to determine how much space our pushed in node gets.
        if dest in removed_nodes:
            dest = next(n for n in dest_ancestors if n not in removed_nodes)

        _, added_nodes, _removed_nodes = self._split(
            dest, axis, insert_node=br_rm, normalize=normalize
        )
        removed_nodes.extend(_removed_nodes)

        self._notify_subscribers(TreeEvent.node_removed, removed_nodes)
        self._notify_subscribers(TreeEvent.node_added, added_nodes)

    def push_in_with_neighbor(
        self,
        node: Node,
        direction: DirectionParam,
        *,
        src_selection: NodeHierarchySelectionMode,
        dest_selection: NodeHierarchySelectionMode,
        normalize: bool = False,
        wrap: bool = False,
    ):
        direction = Direction(direction)

        src = self.resolve_node_selection(node, src_selection, direction)
        dest = self.resolve_node_neighbor_selection(
            node, dest_selection, direction, wrap=wrap
        )

        self.push_in(src, dest, normalize=normalize)

    def pull_out(
        self,
        node: Node,
        *,
        position: Direction1DParam = Direction1D.previous,
        src_selection: NodeHierarchyPullOutSelectionMode = NodeHierarchyPullOutSelectionMode.mru_deepest,
        normalize: bool = False,
    ):
        position = Direction1D(position)

        dummy_direction = Direction.right
        node = self.resolve_node_selection(node, src_selection, dummy_direction)

        try:
            node_to_split = node.get_first_ancestor(SplitContainer)
            split_axis = node_to_split.axis.inv
        except ValueError as ex:
            raise InvalidNodeSelectionError("Invalid node provided to pull out") from ex

        # There are times when we have to pull something out from inside a TC
        if node_to_split.is_nearest_under_tc:
            node_to_split = node_to_split.get_first_ancestor(TabContainer)
            if node_to_split is self.root:
                raise InvalidNodeSelectionError("Invalid node provided to pull out")
            split_axis = node_to_split.parent.axis

        # We capture some info beforehand to be able to deal with one particular edge
        # case: when a pull_out() leads to a TC being discarded and its remnant tab's
        # contents get merged upward.
        # If the remnant tab had multiple children along the split axis, we need to be
        # able to position the pulled out node at the correct pre/post index relative to
        # the merged children.
        node_to_split_container = node_to_split.parent
        node_to_split_index = node_to_split_container.children.index(node_to_split)
        node_to_split_container_orig_child_count = len(node_to_split_container.children)

        removed_nodes = []
        br_rm, _, br_sib, extra_removed_nodes = self._remove(node, normalize=normalize)
        if br_sib is not None:
            removed_nodes.extend(self._do_post_removal_pruning(br_sib))

        # When br_rm resolves to an ancestor node, we can skip passing these additional
        # nodes to `_split(..., insert_node=xxx)` to keep things simple. This
        # effectively means we're doing `_split(..., insert_node=node)`.
        # Important in cases where eg. `br_rm` resolves to a T node.
        if extra_removed_nodes:
            removed_nodes.extend(extra_removed_nodes[1:])
            br_rm = extra_removed_nodes[0]

        # This is again to deal with the one edge case mentioned above.
        # Not happy with this, but it works. All this stems from pruning happening
        # and us losing references to nodes we'd otherwise be working with.
        # Note that one quirk here is that we split the first/last of the remnant child
        # nodes instead of the whole TC's space.
        if node_to_split in removed_nodes:
            if position == Direction1D.next:
                node_to_split_index = node_to_split_index + (
                    len(node_to_split_container.children)
                    - node_to_split_container_orig_child_count
                )

            node_to_split = node_to_split_container.children[node_to_split_index]
            split_axis = node_to_split_container.axis

        _, added_nodes, _removed_nodes = self._split(
            node_to_split,
            split_axis,
            insert_node=br_rm,
            normalize=normalize,
            position=position,
        )
        removed_nodes.extend(_removed_nodes)

        self._notify_subscribers(TreeEvent.node_removed, removed_nodes)
        self._notify_subscribers(TreeEvent.node_added, added_nodes)

    def pull_out_to_tab(self, node: Node, *, normalize: bool = False):
        tc = node.get_first_ancestor(TabContainer)

        # When `node` is the sole top level node under our TC (or is simply a Tab),
        # instead of an effective no-op, pull out to the next higher level TC.
        if (node.is_sole_child and node.is_nearest_under_tc) or isinstance(node, Tab):
            tc = tc.get_first_ancestor(TabContainer)

        removed_nodes = []
        br_rm, _, br_sib, _ = self._remove(node, normalize=normalize)
        if br_sib is not None:
            removed_nodes.extend(self._do_post_removal_pruning(br_sib))

        _, added_nodes = self._add_tab(tc, insert_node=br_rm)

        self._notify_subscribers(TreeEvent.node_removed, removed_nodes)
        self._notify_subscribers(TreeEvent.node_added, added_nodes)

    def is_visible(self, node: Node) -> bool:
        """Whether a node is visible or not. A node is visible if all its ancestor
        tabs are active.
        """
        n = node
        while n.parent is not None:
            if isinstance(n.parent, TabContainer) and n.parent.active_child is not n:
                return False
            n = n.parent
        return True

    def find_border_encompassing_supernode(
        self, node: Node, border_direction: Direction, *, stop_at_tc: bool = False
    ) -> Node | None:
        """
        For the provided `node's` border in the specified `direction`, finds the largest
        ancestor node that `node's` border is a part of.

        The chosen super node is one that is of the correct 'orientation', ie. it is
        under a SC for which `sc.axis == direction.axis`.

        If `stop_at_tc` is provided, then we stop the seach at the nearest TabContainer.

        For the edge cases where there is no such oriented super node, `None` is
        returned. This happens when:
            - `node` is a sole top level pane under the root TC
            - There are only top level panes under the root TC and the requested
              direction is in the inverse direction of those panes.
        """
        # TODO: Better docs for explaining the 'orientation' aspect. Or make it so it is
        # no longer needed.

        supernode = None
        n, p = node, node.parent
        while p is not None:
            if isinstance(p, SplitContainer) and p.axis == border_direction.axis:
                supernode = n
                edge_node = p.children[-1 if border_direction.axis_unit > 0 else 0]
                if n is not edge_node:
                    break
            if stop_at_tc and isinstance(p, TabContainer):
                supernode = p
                break
            n, p = p, p.parent
        return supernode

    def resolve_node_selection(
        self,
        node: Node,
        selection_mode: NodeHierarchySelectionMode,
        border_direction: DirectionParam,
    ):
        mode = NodeHierarchySelectionMode(selection_mode)
        border_direction = Direction(border_direction)

        if mode == NodeHierarchySelectionMode.mru_deepest:
            resolved_node = self.find_mru_pane(start_node=node)
        elif mode == NodeHierarchySelectionMode.mru_largest:
            resolved_node = self.find_border_encompassing_supernode(
                node, border_direction, stop_at_tc=False
            )
        elif mode == NodeHierarchySelectionMode.mru_subtab_else_deepest:
            deepest = self.find_mru_pane(start_node=node)
            tc = deepest.get_first_ancestor(TabContainer)
            resolved_node = tc if tc.tab_level > 1 else deepest
        elif mode == NodeHierarchySelectionMode.mru_subtab_else_largest:
            resolved_node = self.find_border_encompassing_supernode(
                node, border_direction, stop_at_tc=True
            )
        else:
            raise ValueError(f"Invalid `selection_mode`: {selection_mode}")

        return resolved_node

    def resolve_node_neighbor_selection(
        self,
        node: Node,
        selection_mode: NodeHierarchySelectionMode,
        border_direction: DirectionParam,
        *,
        wrap: bool = False,
    ):
        mode = NodeHierarchySelectionMode(selection_mode)
        border_direction = Direction(border_direction)

        adjacent_panes = self.adjacent_panes(node, border_direction, wrap=wrap)
        if not adjacent_panes:
            raise InvalidNodeSelectionError("There is no neighbor node to select.")

        if mode == NodeHierarchySelectionMode.mru_deepest:
            resolved_node = self.find_mru_pane(panes=adjacent_panes)
        elif mode == NodeHierarchySelectionMode.mru_largest:
            besp = self.find_border_encompassing_supernode(
                node, border_direction, stop_at_tc=False
            )
            assert besp is not None
            resolved_node = besp.sibling(border_direction.axis_unit, wrap=wrap)
        elif mode == NodeHierarchySelectionMode.mru_subtab_else_deepest:
            deepest = self.find_mru_pane(panes=adjacent_panes)
            tc = deepest.get_first_ancestor(TabContainer)
            resolved_node = tc if tc.tab_level > 1 else deepest
        elif mode == NodeHierarchySelectionMode.mru_subtab_else_largest:
            deepest = self.find_mru_pane(panes=adjacent_panes)
            tc = deepest.get_first_ancestor(TabContainer)
            if tc.tab_level > 1:
                resolved_node = tc
            else:
                besp = self.find_border_encompassing_supernode(
                    node, border_direction, stop_at_tc=False
                )
                assert besp is not None
                resolved_node = besp.sibling(border_direction.axis_unit, wrap=wrap)
        else:
            raise ValueError(f"Invalid `selection_mode`: {selection_mode}")

        return resolved_node

    def iter_walk(
        self, start: Node | None = None, *, only_visible: bool = False
    ) -> Iterator[Node]:
        if self.is_empty:
            return

        def walk(node: Node) -> Iterator[Node]:
            yield node
            if only_visible and isinstance(node, TabContainer):
                yield from walk(node.active_child)
            else:
                for n in node.children:
                    yield from walk(n)

        yield from walk(start or self._root)

    def iter_panes(
        self, visible: bool | None = None, start: Node | None = None
    ) -> Iterator[Pane]:
        if self.is_empty:
            return

        for node in self.iter_walk(start):
            if isinstance(node, Pane):
                if visible is not None:
                    if self.is_visible(node) == visible:
                        yield node
                else:
                    yield node

    def find_mru_pane(
        self, *, start_node: Node | None = None, panes: Iterable[Pane] | None = None
    ) -> Pane:
        if start_node is not None and panes is not None:
            raise ValueError(
                "Either of `panes` or `start_node` can be provided, but not both."
            )

        candidates = panes if panes is not None else self.iter_panes(start=start_node)
        return sorted(candidates, key=lambda p: p.recency, reverse=True)[0]

    def subscribe(self, event: TreeEvent, callback: Tree.TreeEventCallback) -> str:
        subscription_id = uuid.uuid4().hex
        self._event_subscribers[event][subscription_id] = callback
        return subscription_id

    def unsubscribe(self, subscription_id: str):
        for subscribers in self._event_subscribers.values():
            if subscription_id in subscribers:
                del subscribers[subscription_id]
                return

    def clone(self) -> Tree:
        clone = self.__class__(self.width, self.height, self._config)
        current_state = self.as_dict()
        clone.reset(from_state=current_state)
        return clone

    def reevaluate_dynamic_attributes(self, start_node: Node | None = None):
        """Walks down the provided `start_node` and re-applies any dynamic
        configuration.
        eg. tab-level-dependent config, tab-bar hide/show scenarios, etc.

        💭 This has evolved into something of a general purpose 'second pass' over the
        tree to re-calculate some properties. It is now invoked after various tree
        operations. This is opposed to in-place checking and tweaking of various
        attributes in places that might impact them - which was starting to get unweildy
        as codebase grew.
        💭 I wonder if the post-removal tree-pruning operations could also be part of
        this 2nd pass.
        """
        for node in self.iter_walk(start=start_node):
            tab_level = node.tab_level
            if isinstance(node, TabContainer):
                self.handle_bar_hiding_config(node)
            elif isinstance(node, Pane):
                margin: int = self.get_config("window.margin", level=tab_level)
                border: int = self.get_config("window.border_size", level=tab_level)
                padding: int = self.get_config("window.padding", level=tab_level)
                if node.tab_level == 1 and node.is_sole_child:
                    margin = self.get_config("window.single.margin", default=margin)
                    border = self.get_config(
                        "window.single.border_size", default=border
                    )
                    padding = self.get_config("window.single.padding", default=padding)
                node.box.margin = margin
                node.box.border = border
                node.box.padding = padding

    def handle_bar_hiding_config(self, tc: TabContainer):
        hide_when: str = self.get_config("tab_bar.hide_when", level=tc.tab_level)
        if hide_when == "always" or (hide_when == "single_tab" and tc.has_single_child):
            tc.collapse_tab_bar()
        else:
            bar_height: int = self.get_config("tab_bar.height", level=tc.tab_level)
            tc.expand_tab_bar(bar_height)

    def as_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "root": None if self.is_empty else self.root.as_dict(),
        }

    @classmethod
    def next_recency_value(cls):
        cls._recency_seq += 1
        return cls._recency_seq

    def __repr__(self) -> str:
        if self.is_empty:
            return "<empty>"

        def walk(node, prefix=""):
            frags = [f"{prefix}- {node}"]
            for n in node.children:
                frags.extend(walk(n, prefix + 4 * " "))
            return frags

        return "\n".join(walk(self._root))

    def _split(
        self,
        node: Node,
        axis: Axis,
        *,
        ratio: float = 0.5,
        normalize: bool = False,
        insert_node: Node | None = None,
        position: Direction1D = Direction1D.next,
    ) -> tuple[Node, list[Node], list[Node]]:
        validate_unit_range(ratio, "ratio")
        try:
            node.get_self_or_first_ancestor(SplitContainer)
        except ValueError as ex:
            raise InvalidNodeSelectionError("Invalid node provided to split") from ex
        if isinstance(insert_node, Tab):
            raise ValueError(
                "`insert_node` cannot be a Tab instance. Tabs can only live under"
                "TabContainers."
            )

        self._maybe_invert_top_level_sc(node, axis)

        added_nodes = []
        removed_nodes = []
        container, node_to_split, new_index = node.get_participants_for_split_op(
            axis, position
        )
        if container is None:
            # We need a new intermediate SC
            sc = self.create_split_container()
            sc.axis = axis
            added_nodes.append(sc)

            anchor = node_to_split.parent

            node_index = anchor.children.index(node_to_split)
            anchor.children.remove(node_to_split)
            node_to_split.parent = None

            anchor.children.insert(node_index, sc)
            sc.parent = anchor

            node_to_split.parent = sc
            sc.children = [node_to_split]

            container = sc

        n1_rect, n2_rect = node_to_split.principal_rect.split(axis, ratio)
        if position == Direction1D.previous:
            n1_rect, n2_rect = n2_rect, n1_rect

        node_to_split.transform(axis, n1_rect.coord(axis), n1_rect.size(axis))

        assert isinstance(container, SplitContainer)

        if insert_node is None:
            new_content = self.create_pane(n2_rect, tab_level=container.tab_level)
            added_nodes.append(new_content)
            new_content.parent = container
            container.children.insert(new_index, new_content)
        else:
            insert_node.transform(Axis.x, n2_rect.x, n2_rect.w)
            insert_node.transform(Axis.y, n2_rect.y, n2_rect.h)

            if isinstance(insert_node, SplitContainer) and insert_node.axis == axis:
                for n in insert_node.children:
                    n.parent = container
                container.children[new_index:new_index] = insert_node.children
                removed_nodes.append(insert_node)

                # Bit of an odd scenario here. `insert_node` and `container` are
                # essentially merged and there is no clear 'new_content' branch. We just
                # mark the participating container as being the new content.
                new_content = container
            else:
                new_content = insert_node
                new_content.parent = container
                container.children.insert(new_index, new_content)

        self.reevaluate_dynamic_attributes(container.parent)
        if normalize:
            self.normalize(container)

        return new_content, added_nodes, removed_nodes

    def _remove(
        self, node: Node, *, consume_vacant_space: bool = True, normalize: bool = False
    ) -> tuple[Node, int, Node | None, list[Node]]:
        """Internal helper for removing node subtrees.

        Returns:
            A 4-tuple with the following items:
                1. The resolved node that is the point of removal. May be the provided
                `node` or an ancestor.
                2. The position index of the removed node under its parent.
                3. The sibling of the removed node.
                4. List of additional nodes to be removed between the provided `node`
                and the resolved ancestor node in tuple.0.
        """
        br_rm, br_rm_nodes = self._find_removal_branch(node)
        if br_rm is self._root:
            return (br_rm, 0, None, br_rm_nodes)

        container = br_rm.parent
        br_rm_pos = container.children.index(br_rm)
        br_sib = br_rm.operational_sibling
        union_rect = br_rm.principal_rect.union(br_sib.principal_rect)

        container.children.remove(br_rm)
        br_rm.parent = None

        assert br_sib is not None

        if consume_vacant_space:
            br_sib.transform(Axis.x, union_rect.x, union_rect.w)
            br_sib.transform(Axis.y, union_rect.y, union_rect.h)
            if normalize and isinstance(container, SplitContainer):
                self.normalize(container)
            elif isinstance(container, TabContainer):
                container.active_child = container.children[br_rm_pos - 1]

        self.reevaluate_dynamic_attributes(br_rm.parent)

        return (br_rm, br_rm_pos, br_sib, br_rm_nodes)

    def _get_pruning_cases(self) -> list[_PruningCase]:
        return [
            _PruningCase(
                chain=(SplitContainer, SplitContainer, Pane), prune=self._prune_sc_sc_p
            ),
            _PruningCase(
                chain=(Tab, SplitContainer, SplitContainer), prune=self._prune_t_sc_sc
            ),
            _PruningCase(
                chain=(SplitContainer, SplitContainer, SplitContainer),
                prune=self._prune_sc_sc_sc,
            ),
            _PruningCase(
                chain=(SplitContainer, SplitContainer, TabContainer),
                prune=self._prune_sc_sc_tc,
            ),
            _PruningCase(
                chain=(SplitContainer, TabContainer, Tab),
                prune=self._prune_sc_tc_t,
            ),
            _PruningCase(
                chain=(type(None), TabContainer, Tab),
                prune=self._prune_none_tc_t,
            ),
        ]

    def _add_very_first_tab(self) -> tuple[Tab, list[Node]]:
        """Add the first tab and its pane on an empty tree. A special case where the
        root is set and initial rects are set for use by all subsequent tabs and panes.
        """
        added_nodes = []

        top_level = 1
        tc = self.create_tab_container()
        tc.tab_bar = self._build_tab_bar(0, 0, self.width, top_level, 1)
        added_nodes.append(tc)

        # Max sized rect to start things off
        tc_rect = Rect(0, 0, self.width, self.height)

        # Make sure to set root here, so any tab-level reads in `_add_tab` have a
        # reference point.
        self._root = tc

        t, _added_nodes = self._add_tab(tc, tc_rect=tc_rect)
        added_nodes.extend(_added_nodes)

        return t, added_nodes

    def _add_tab(
        self,
        tc: TabContainer,
        *,
        insert_node: Node | None = None,
        tc_rect: Rect | None = None,
        focus_new: bool = True,
    ) -> tuple[Tab, list[Node]]:
        """Add a new tab to the provided TabContainer instance.

        Args:
            `tc`:
                The TabContainer instance under which the new tab should be added.
            `insert_node`:
                If provided, add the provided branch under the new tab. Or if the node
                provided is a `Tab`, just use that.
                If nothing is provided, a new Pane instance is created to add under the
                new tab.
            `tc_rect`:
                If provided, this Rect will be used determine the dimensions of the new
                tab. Else will determine dimensions from the provided `tc`.
                Used primarily when adding a tab to a brand new TabContainer that
                doesn't have any children yet.
            `focus_new`:
                If True, will make the newly added tab the active one.

        Returns:
            A 2-tuple with:
                1. The new `Tab` node instance.
                2. The list of newly created nodes.
        """
        if not tc.children and tc_rect is None:
            raise ValueError(
                "If `tc` has no children to obtain a Rect from, a `tc_content_rect` "
                "must be provided."
            )

        # self._ensure_tab_bar_restored(tc)

        tc_rect = Rect.from_rect(tc.principal_rect) if tc_rect is None else tc_rect
        bar_rect = tc.tab_bar.box.principal_rect
        tc_content_rect = Rect(
            tc_rect.x, bar_rect.y2, tc_rect.w, tc_rect.h - bar_rect.h
        )

        def _transform_tab(t: Tab):
            t.transform(Axis.x, tc_content_rect.x, tc_content_rect.w)
            t.transform(Axis.y, tc_content_rect.y, tc_content_rect.h)

        added_nodes = []

        # Handle the need for a T under the TC
        if isinstance(insert_node, Tab):
            t = insert_node
            t.parent = tc
            tc.children.append(t)
            if focus_new:
                tc.active_child = t
            _transform_tab(t)
            return (t, added_nodes)
        t = self.create_tab()
        t.parent = tc
        tc.children.append(t)
        added_nodes.append(t)
        if focus_new:
            tc.active_child = t

        # Handle the need for a SC under the T
        if isinstance(insert_node, SplitContainer):
            sc = insert_node
            sc.parent = t
            t.children.append(sc)
            _transform_tab(t)
            return (t, added_nodes)
        sc = self.create_split_container()
        sc.parent = t
        t.children.append(sc)
        added_nodes.append(sc)

        # Handle the need for content under the SC. Can be P or TC.
        if insert_node is not None:
            content = insert_node
        else:
            content = self.create_pane(tc_content_rect, tab_level=tc.tab_level)
            added_nodes.append(content)
        content.parent = sc
        sc.children.append(content)

        _transform_tab(t)
        self.reevaluate_dynamic_attributes(start_node=tc)

        return (t, added_nodes)

    def _add_tab_at_new_level(
        self, at_node: Node, insert_node: Node | None = None
    ) -> tuple[Node, list[Node]]:
        """Converts the provided `at_node` into a subtab tree, placing `at_node` as the
        first tab in the new level, and creates a new second tab in that subtab tree.

        If `insert_node` is provided, it is inserted under the new tab. Else we create a
        new pane to place there instead.
        """
        added_nodes = []

        # Find the nearest SplitContainer under which tabbing should happen
        try:
            at_node, at_container = next(
                (n, n.parent)
                for n in at_node.get_ancestors(include_self=True)
                if isinstance(n.parent, SplitContainer)
            )
        except StopIteration:
            raise ValueError(
                "Invalid node provided to tab on. No ancestor SplitContainer found."
            ) from None

        # Freeze some attributes to use in subsequent operations
        at_node_rect = Rect.from_rect(at_node.principal_rect)
        new_tab_level = at_node.tab_level + 1

        # Remove `at_node` from tree so we can begin to insert a new tab container
        # subtree. We add it back later as a leaf under the new subtree.
        at_node_pos = at_container.children.index(at_node)
        at_node.parent = None
        at_container.children.remove(at_node)

        tc = self.create_tab_container()
        tc.parent = at_container
        at_container.children.insert(at_node_pos, tc)
        tc.tab_bar = self._build_tab_bar(
            at_node.principal_rect.x,
            at_node.principal_rect.y,
            at_node.principal_rect.w,
            new_tab_level,
            2,
        )
        added_nodes.append(tc)

        _, _added_nodes = self._add_tab(tc, insert_node=at_node, tc_rect=at_node_rect)
        added_nodes.extend(_added_nodes)

        _, _added_nodes = self._add_tab(
            tc, insert_node=insert_node, tc_rect=at_node_rect
        )
        added_nodes.extend(_added_nodes)

        return tc, added_nodes

    def _build_tab_bar(
        self, x: int, y: int, w: int, tab_level: int, tab_count: int
    ) -> TabBar:
        bar_height = self.get_config("tab_bar.height", level=tab_level)

        # hide the tab bar when relevant, by setting its height to 0
        bar_hide_when = self.get_config("tab_bar.hide_when", level=tab_level)
        if bar_hide_when == "always" or (
            bar_hide_when == "single_tab" and tab_count == 1
        ):
            bar_height = 0

        return TabBar(
            principal_rect=Rect(x, y, w, bar_height),
            margin=self.get_config("tab_bar.margin", level=tab_level),
            border=self.get_config("tab_bar.border_size", level=tab_level),
            padding=self.get_config("tab_bar.padding", level=tab_level),
        )

    def _maybe_invert_top_level_sc(self, node: Node, requested_axis: Axis):
        if not isinstance(node, SplitContainer):
            node = node.get_first_ancestor(SplitContainer)
        if (
            node.axis != requested_axis
            and node.is_nearest_under_tc
            and node.has_single_child
        ):
            node.axis = requested_axis

    def _find_removal_branch(self, node: Node) -> tuple[Node, list[Node]]:
        n = node
        nodes_to_remove: list[Node] = [n]
        while n is not self._root and n.is_sole_child:
            n = n.parent
            nodes_to_remove.append(n)
        return n, nodes_to_remove

    def _do_post_removal_pruning(self, node: Node) -> list[Node]:
        """After a removal operation, optimizes the tree to keep it minimal by
        discarding nodes that are now unnecessary to keep the same semantic tree.

        This arises when the provided `node` is now a sole remnant child wrt its parent.
        We take `node` and look at its two ancestors, `n2` and `n1`, giving us a
        top-down chain of `[n1, n2, n3]`.

        We then look for opportunities to merge `n3` or its children into `n1` and
        discard whatever nodes we can. The tree configuration options can also play a
        role in determining whether or not pruning happens.

        All the `[n1, n2, n3]` possibilities are listed below.
        The arrows point to the parent node. The chains that are prunable are marked
        with *.

            T ◄─┐
                │
                ├── SC ◄───── P
                │
          *SC ◄─┘

           TC ◄────  T ◄───┐
                           ├─ SC
                           │
           *T ◄──┬─ SC ◄───┘
                 │
                 │
          *SC ◄──┘

          *SC ◄─┐
                │
                ├── TC ◄────── T
                │
        *None ◄─┘

            T ◄─┐
                │
                ├── SC ◄────── TC
                │
          *SC ◄─┘


        Note that the case of `TC ◄─ T ◄─ SC` cannot occur after a removal operation. As
        a T can only ever have a single child.
        """
        nodes_to_remove = []
        n1, n2, n3 = node.parent.parent, node.parent, node

        if n3.is_sole_child:
            active_pruning_case = next(
                (
                    case
                    for case in self._pruning_cases
                    if all(
                        [
                            isinstance(n1, case.chain[0]),
                            isinstance(n2, case.chain[1]),
                            isinstance(n3, case.chain[2]),
                        ]
                    )
                ),
                None,
            )
            if active_pruning_case is not None:
                nodes_to_remove.extend(active_pruning_case.prune(n1, n2, n3))

        return nodes_to_remove

    def _prune_sc_sc_p(
        self, n1: SplitContainer, n2: SplitContainer, n3: Pane
    ) -> list[Node]:
        """n1 and n3 are linked together, n2 is discarded."""
        n2_position = n1.children.index(n2)
        n1.children.remove(n2)
        n3.parent = n1
        n1.children.insert(n2_position, n3)
        return [n2]

    def _prune_t_sc_sc(
        self, n1: Tab, n2: SplitContainer, n3: SplitContainer
    ) -> list[Node]:
        """n1 and n3 are linked together, n2 is discarded."""
        n2_position = n1.children.index(n2)
        n1.children.remove(n2)
        n3.parent = n1
        n1.children.insert(n2_position, n3)
        return [n2]

    def _prune_sc_sc_sc(
        self, n1: SplitContainer, n2: SplitContainer, n3: SplitContainer
    ) -> list[Node]:
        """n1 absorbs the children of n3. n2 and n3 are discarded."""
        n2_position = n1.children.index(n2)
        n1.children.remove(n2)
        for child in n3.children:
            child.parent = n1
            n1.children.insert(n2_position, child)
            n2_position += 1
        return [n3, n2]

    def _prune_sc_sc_tc(
        self, n1: SplitContainer, n2: SplitContainer, n3: TabContainer
    ) -> list[Node]:
        """n1 and n3 are linked together, n2 is discarded."""
        n2_position = n1.children.index(n2)
        n1.children.remove(n2)
        n3.parent = n1
        n1.children.insert(n2_position, n3)
        return [n2]

    def _prune_sc_tc_t(
        self, n1: SplitContainer, n2: TabContainer, n3: Tab
    ) -> list[Node]:
        """Depending on what is configured, this may lead to elimination of a subtab
        level - so n2 and n3 get discarded, linking n1 with n3's children.

        If the above pruning does happen, it leaves us with another possible opportunity
        to prune things if n1 and n3's child SC are of the same orientation.

        Elimination of a TC also leads to geometry adjustments due to the TC's tab bar
        also being eliminated.
        """
        removed_nodes = []
        hide_when = self.get_config("tab_bar.hide_when", level=n3.tab_level)
        if hide_when in ["always", "single_tab"]:
            n2_position = n1.children.index(n2)
            n1.children.remove(n2)
            sc = n3.children[0]

            # n3's T can only have a single SC child. The sc can now either match the n1
            # SC orientation or be different. Alternatively, the sc could also have been
            # holding a sole pane under the final tab of a lower level TC. In all cases,
            # we perform the appropriate merging.
            if (sc.axis == n1.axis) or sc.has_single_child:
                for child in sc.children:
                    child.parent = n1
                    n1.children.insert(n2_position, child)
                    n2_position += 1
                removed_nodes.append(sc)
            else:
                sc.parent = n1
                n1.children.insert(n2_position, sc)

            removed_nodes.extend([n3, n2])

            # Consume space left by tab bar after n2 is eliminated
            sc.transform(
                Axis.y,
                n2.principal_rect.y,
                sc.principal_rect.h + n2.tab_bar.box.principal_rect.h,
            )

        return removed_nodes

    def _prune_none_tc_t(self, n1: None, n2: TabContainer, n3: Tab) -> list[Node]:
        """As n1 is `None`, this is only applicable at the topmost tab level. There's no
        'pruning' per se, but when `tab_bar.hide_when` is configured to be `single_tab`,
        we need to hide the tab bar in this case.

        So only geometry adjustments are made to consume the space of the hidden tab
        bar.
        """
        hide_when: str = self.get_config("tab_bar.hide_when", level=n3.tab_level)
        if hide_when == "single_tab":
            n2.collapse_tab_bar()
        return []

    def _parse_state(self, state: dict) -> TabContainer | None:
        # Just basic validation in a few places. We could go all out with a schema
        # validator, but this is ok for now.

        if set(state.keys()) != {"width", "height", "root"}:
            raise ValueError("The provided tree state is not in an expected format")

        if state["root"] is None:
            return None

        seen_ids = set()

        def walk_and_create(n, parent) -> Node:
            node_type = n["type"]

            node_id = n["id"]
            if node_id in seen_ids:
                raise ValueError("The provided tree state has nodes with duplicate IDs")
            seen_ids.add(node_id)

            if node_type == TabContainer.abbrv():
                tc = self.create_tab_container()
                tc.id = node_id
                bar_rect_state = n["tab_bar"]["box"]["principal_rect"]
                tc.tab_bar = self._build_tab_bar(
                    bar_rect_state["x"],
                    bar_rect_state["y"],
                    bar_rect_state["w"],
                    parent.tab_level + 1 if parent is not None else 1,
                    len(n["children"]),
                )
                tc.parent = parent
                tc.children = [walk_and_create(c, tc) for c in n["children"]]
                tc.active_child = next(
                    (c for c in tc.children if c.id == n["active_child"]), None
                )
                return tc
            elif node_type == Tab.abbrv():
                t = self.create_tab()
                t.id = node_id
                t.title = n["title"]
                t.parent = parent
                t.children = [walk_and_create(c, t) for c in n["children"]]
                return t
            elif node_type == SplitContainer.abbrv():
                sc = self.create_split_container()
                sc.id = node_id
                sc.axis = Axis(n["axis"])
                sc.parent = parent
                sc.children = [walk_and_create(c, sc) for c in n["children"]]
                return sc
            elif node_type == Pane.abbrv():
                principal_rect = Rect(**n["box"]["principal_rect"])
                p = self.create_pane(principal_rect=principal_rect)
                p.id = node_id
                p.parent = parent
                return p

            raise ValueError("The provided tree state has nodes of unknown type")

        return walk_and_create(state["root"], None)

    def _find_super_node_to_resize(self, pane: Pane, axis: Axis) -> Node | None:
        """Finds the first node in the ancestor chain that is under a SC of the
        specified `axis`.
        """
        super_node = None
        n, p = pane, pane.parent
        while p is not None:
            if isinstance(p, SplitContainer):
                # A sole pane under a nested TC is a special case. During resize, it
                # behaves as if it were directly under said TC's container.
                n_is_sole_top_level_node = p.is_nearest_under_tc and p.has_single_child
                if not n_is_sole_top_level_node and p.axis == axis:
                    super_node = n
                    break
            n, p = p, p.parent
        return super_node

    def _find_panes_along_border(self, node: Node, direction: Direction) -> list[Pane]:
        if isinstance(node, Pane):
            return [node]

        if isinstance(node, TabContainer):
            sc = node.active_child.children[0]
            return self._find_panes_along_border(sc, direction)

        assert isinstance(node, SplitContainer)
        if node.axis == direction.axis:
            edge_node = node.children[0 if direction.axis_unit > 0 else -1]
            return self._find_panes_along_border(edge_node, direction)

        panes = []
        for inv_axis_child in node.children:
            panes.extend(self._find_panes_along_border(inv_axis_child, direction))
        return panes

    def _next_tab(
        self, node: Node, n: int, *, level: int = -1, wrap: bool = True
    ) -> Pane | None:
        ancestor_tabs = list(reversed(node.get_ancestors(Tab, include_self=True)))
        if not ancestor_tabs:
            raise ValueError("The provided node is not under a `TabContainer` node")
        if not (level == -1 or 0 < level <= len(ancestor_tabs)):
            raise ValueError(
                "The provided `level` is invalid. It must be within `node.tab_level` "
                "or be `-1`."
            )

        if level == -1:
            level = len(ancestor_tabs)
        ancestor_tab = ancestor_tabs[level - 1]

        next_tab = ancestor_tab.sibling(n, wrap=wrap)
        if next_tab is None:
            return None

        return self.find_mru_pane(start_node=next_tab)

    def _notify_subscribers(self, event: TreeEvent, nodes: list[Node]):
        if nodes:
            for callback in self._event_subscribers[event].values():
                callback(nodes)

    def _validate_tab_bar_config(self, level: int):
        bar_height = self.get_config(
            "tab_bar.height", level=level, fall_back_to_base_level=True
        )
        bar_margin = self.get_config(
            "tab_bar.margin", level=level, fall_back_to_base_level=True
        )
        bar_border_size = self.get_config(
            "tab_bar.border_size", level=level, fall_back_to_base_level=True
        )
        bar_padding = self.get_config(
            "tab_bar.padding", level=level, fall_back_to_base_level=True
        )
        try:
            Box(
                Rect(0, 0, self.width, bar_height),
                margin=bar_margin,
                border=bar_border_size,
                padding=bar_padding,
            ).validate()
        except ValueError as err:
            raise ValueError(f"Error in tab_bar config. {err}") from err


def tree_matches_repr(tree: Tree, test_str: str) -> bool:
    """Tests if the provided `Tree` instance has a str representation that matches the
    provided tree str representation in `test_str`.
    """
    tree_str = textwrap.dedent(str(tree)).strip()
    test_str = textwrap.dedent(test_str).strip()
    return tree_str == test_str


def tree_repr_matches_repr(str1: str, str2: str) -> bool:
    str1 = textwrap.dedent(str1).strip()
    str2 = textwrap.dedent(str2).strip()
    return str1 == str2
