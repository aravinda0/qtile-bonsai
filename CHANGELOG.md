## v0.5.0 [2024-12-30]

### Features & Improvements

- `window.default_add_mode` now supports additional options: `split_x`, `split_y`, `<custom-callback>`. These provide more control for 'automatic' window addition workflows. (#13)
- The `next_tab()`, `prev_tab()` and `swap_tabs()` layout commands now support a `level` parameter. Allows for more control with keybinds when subtabs are in play.

### Fixes

- Fixed a packaging issue that prevented installation under Python 3.13 (#15)

### Miscellaneous

- The package is now available in [nixpgks](https://search.nixos.org/packages?channel=unstable&from=0&size=50&sort=relevance&type=packages&query=qtile-bonsai) as `qtile-bonsai`. Thanks @Gurjaka, @Sigmanificient, @saviola777 !


## v0.4.0 [2024-08-17]

### Features & Improvements

- New layout options `window.single.margin` and `window.single.border_size` allow specifying margin, border for single windows under top-level tabs. (#10)
- New widget option `sync_with` on `BonsaiBar` to control which (screen's) `Bonsai` layout state is rendered on the widget. (#9)
- New layout option `tab_bar.hide_L1_when_bonsai_bar_on_screen` makes multi-screen setups smoother. 
    - The L1 (top level) tab bar can be hidden away if there is a `BonsaiBar` widget available on a screen, and the bar would be shown if there was not a widget present.
    - This also makes the `BonsaiBar` widget usage simpler - we no longer need to configure `L1.tab_bar.hide_when = "always"` on our layout to explicitly hide away the L1 bar.

### Fixes

- Fullscreening windows should work properly now. (#11)
- Fix a typo that was causing the BonsaiBar widget to not clean up properly on reload/restart
- Fixed an obscure bug where in some rare cases, killing a background window would not focus the correct MRU window.


## v0.3.0 [2024-07-10]
                                   

### Features & Improvements

- The `BonsaiBar` widget now supports `tab.width = "auto"` just like the `Bonsai` layout's `tab_bar.tab.width`. Tabs will fit to take up as much available space as possible. (#8)
- The `BonsaiBar` widget's `length` config now supports the special values `bar.CALCULATED` and `bar.STRETCH` like other qtile widgets. 
- Tabs in both the `Bonsai` layout and the `BonsaiBar` widget can now be configured with 4-sided values for margin and padding. Values can be provided in the usual [top, right, bottom, left] sequence.

### Fixes

- Window-title changes are now correctly handled for updating tab titles. Previously it didn't used to trigger a re-render until you switched focus to a different window. (#7)

### Miscellaneous

- You can now install the package from the AUR with your favorite AUR-helper. For example: `yay -S qtile-bonsai` 


## v0.2.0 [2024-07-06]
                                   

### Breaking Changes

- The `tab_bar.tab.min_width` has been dropped in favor of `tab_bar.tab.width` which can
  take an integer or the value `"auto"`. (#3)
  - So tabs can either be of fixed width or have an automatic flex-width based
    on available space. Check the docs for more details. 

### Features & Improvements

- A new interaction mode called `container-select-mode` is now available that lets you
  visually select parents/containers of windows and invoke split/tab operations over
  larger areas.
    - A new section has been [added in the visual guide](https://aravinda0.github.io/qtile-bonsai/static/visual_guide/#Container%20Select%20Mode) to demonstrate this.
    - Check the [commands docs](https://github.com/aravinda0/qtile-bonsai?tab=readme-ov-file#layout-commands) for details on the 3 new commands added for this mode.
- A new `BonsaiBar` widget is available for use on the qtile bar. It can act as a replacement for the `Bonsai` layout's built-in tab-bar for the outermost/top-level tabs. It also has an indicator for when `branch-select-mode` is active. (#5)
    - A [new documentation section](https://github.com/aravinda0/qtile-bonsai?tab=readme-ov-file#bonsaibar-widget) has been added for it. 
- Two new commands - `focus_nth_tab()`, `focus_nth_window()` - are now available that
  allow faster access to tabs/windows via keybindings. They provide params that allow
  contextual nth selections.
    - Two new sections have been [added in the visual guide](https://aravinda0.github.io/qtile-bonsai/static/visual_guide/#Focus%20nth%20Tab) to demonstrate them.
    - Check the [commands docs](https://github.com/aravinda0/qtile-bonsai?tab=readme-ov-file#layout-commands) for details.
- There is now basic mouse support - clicking on individual tabs on tab-bars will activate
  the corresponding tab. (#4)
- When there are no windows open yet, and `spawn_split()` is invoked, it now conveniently
  creates the first window. Previously you had to start things off with a `spawn_tab()`. 
- A new config option `tab_bar.tab.title_provider` is available that lets you control the
  title on tabs via a callback function. 
  - For example, you could configure it to have the title of the focused window
    under the tab. Check the docs for the signature and a sample implementation.

### Miscellaneous

- The default colors for borders and tab background/foregrounds have been tweaked to be a
  little more vivid.


## v0.1.0 [2024-05-05]
                                   
First official release. Too many things to list - should have launched way
earlier.
