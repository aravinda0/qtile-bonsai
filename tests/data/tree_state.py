# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


def make_complex_tree_state():
    return {
        "width": 400,
        "height": 300,
        "root": {
            "type": "tc",
            "id": 1,
            "active_child": 2,
            "tab_bar": {
                "box": {
                    "principal_rect": {
                        "x": 0,
                        "y": 0,
                        "w": 400,
                        "h": 20,
                    },
                    "margin": {"top": 0, "right": 0, "bottom": 0, "left": 0},
                    "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0},
                    "border": {"top": 0, "right": 0, "bottom": 0, "left": 0},
                }
            },
            "children": [
                {
                    "type": "t",
                    "id": 2,
                    "title": "",
                    "children": [
                        {
                            "type": "sc",
                            "id": 3,
                            "axis": "x",
                            "children": [
                                {
                                    "type": "p",
                                    "id": 4,
                                    "box": {
                                        "principal_rect": {
                                            "x": 0,
                                            "y": 20,
                                            "w": 200,
                                            "h": 280,
                                        },
                                        "margin": {
                                            "top": 5,
                                            "right": 10,
                                            "bottom": 5,
                                            "left": 20,
                                        },
                                        "border": {
                                            "top": 2,
                                            "right": 2,
                                            "bottom": 2,
                                            "left": 2,
                                        },
                                        "padding": {
                                            "top": 3,
                                            "right": 3,
                                            "bottom": 3,
                                            "left": 3,
                                        },
                                    },
                                    "children": [],
                                },
                                {
                                    "type": "sc",
                                    "id": 6,
                                    "axis": "y",
                                    "children": [
                                        {
                                            "type": "p",
                                            "id": 5,
                                            "box": {
                                                "principal_rect": {
                                                    "x": 200,
                                                    "y": 20,
                                                    "w": 200,
                                                    "h": 140,
                                                },
                                                "margin": {
                                                    "top": 5,
                                                    "right": 10,
                                                    "bottom": 5,
                                                    "left": 20,
                                                },
                                                "border": {
                                                    "top": 2,
                                                    "right": 2,
                                                    "bottom": 2,
                                                    "left": 2,
                                                },
                                                "padding": {
                                                    "top": 3,
                                                    "right": 3,
                                                    "bottom": 3,
                                                    "left": 3,
                                                },
                                            },
                                            "children": [],
                                        },
                                        {
                                            "type": "tc",
                                            "id": 8,
                                            "active_child": 9,
                                            "tab_bar": {
                                                "box": {
                                                    "principal_rect": {
                                                        "x": 200,
                                                        "y": 160,
                                                        "w": 200,
                                                        "h": 20,
                                                    },
                                                    "margin": {
                                                        "top": 0,
                                                        "right": 0,
                                                        "bottom": 0,
                                                        "left": 0,
                                                    },
                                                    "padding": {
                                                        "top": 0,
                                                        "right": 0,
                                                        "bottom": 0,
                                                        "left": 0,
                                                    },
                                                    "border": {
                                                        "top": 0,
                                                        "right": 0,
                                                        "bottom": 0,
                                                        "left": 0,
                                                    },
                                                }
                                            },
                                            "children": [
                                                {
                                                    "type": "t",
                                                    "id": 9,
                                                    "title": "",
                                                    "children": [
                                                        {
                                                            "type": "sc",
                                                            "id": 10,
                                                            "axis": "x",
                                                            "children": [
                                                                {
                                                                    "type": "p",
                                                                    "id": 7,
                                                                    "box": {
                                                                        "principal_rect": {
                                                                            "x": 200,
                                                                            "y": 180,
                                                                            "w": 200,
                                                                            "h": 120,
                                                                        },
                                                                        "margin": {
                                                                            "top": 5,
                                                                            "right": 10,
                                                                            "bottom": 5,
                                                                            "left": 20,
                                                                        },
                                                                        "border": {
                                                                            "top": 2,
                                                                            "right": 2,
                                                                            "bottom": 2,
                                                                            "left": 2,
                                                                        },
                                                                        "padding": {
                                                                            "top": 3,
                                                                            "right": 3,
                                                                            "bottom": 3,
                                                                            "left": 3,
                                                                        },
                                                                    },
                                                                    "children": [],
                                                                },
                                                            ],
                                                        }
                                                    ],
                                                },
                                                {
                                                    "type": "t",
                                                    "id": 11,
                                                    "title": "",
                                                    "children": [
                                                        {
                                                            "type": "sc",
                                                            "id": 12,
                                                            "axis": "y",
                                                            "children": [
                                                                {
                                                                    "type": "p",
                                                                    "id": 13,
                                                                    "box": {
                                                                        "principal_rect": {
                                                                            "x": 200,
                                                                            "y": 180,
                                                                            "w": 200,
                                                                            "h": 60,
                                                                        },
                                                                        "margin": {
                                                                            "top": 5,
                                                                            "right": 10,
                                                                            "bottom": 5,
                                                                            "left": 20,
                                                                        },
                                                                        "border": {
                                                                            "top": 2,
                                                                            "right": 2,
                                                                            "bottom": 2,
                                                                            "left": 2,
                                                                        },
                                                                        "padding": {
                                                                            "top": 3,
                                                                            "right": 3,
                                                                            "bottom": 3,
                                                                            "left": 3,
                                                                        },
                                                                    },
                                                                    "children": [],
                                                                },
                                                                {
                                                                    "type": "p",
                                                                    "id": 14,
                                                                    "box": {
                                                                        "principal_rect": {
                                                                            "x": 200,
                                                                            "y": 240,
                                                                            "w": 200,
                                                                            "h": 60,
                                                                        },
                                                                        "margin": {
                                                                            "top": 5,
                                                                            "right": 10,
                                                                            "bottom": 5,
                                                                            "left": 20,
                                                                        },
                                                                        "border": {
                                                                            "top": 2,
                                                                            "right": 2,
                                                                            "bottom": 2,
                                                                            "left": 2,
                                                                        },
                                                                        "padding": {
                                                                            "top": 3,
                                                                            "right": 3,
                                                                            "bottom": 3,
                                                                            "left": 3,
                                                                        },
                                                                    },
                                                                    "children": [],
                                                                },
                                                            ],
                                                        }
                                                    ],
                                                },
                                            ],
                                        },
                                    ],
                                },
                            ],
                        }
                    ],
                }
            ],
        },
    }


def make_tree_state_with_subtab():
    return {
        "width": 400,
        "height": 300,
        "root": {
            "type": "tc",
            "id": 1,
            "active_child": 2,
            "children": [
                {
                    "type": "t",
                    "id": 2,
                    "children": [
                        {
                            "type": "sc",
                            "id": 3,
                            "children": [
                                {
                                    "type": "p",
                                    "id": 4,
                                    "children": [],
                                    "box": {
                                        "principal_rect": {
                                            "x": 0,
                                            "y": 20,
                                            "w": 200,
                                            "h": 280,
                                        },
                                        "margin": {
                                            "top": 0,
                                            "right": 0,
                                            "bottom": 0,
                                            "left": 0,
                                        },
                                        "border": {
                                            "top": 1,
                                            "right": 1,
                                            "bottom": 1,
                                            "left": 1,
                                        },
                                        "padding": {
                                            "top": 0,
                                            "right": 0,
                                            "bottom": 0,
                                            "left": 0,
                                        },
                                    },
                                },
                                {
                                    "type": "tc",
                                    "id": 6,
                                    "active_child": 9,
                                    "children": [
                                        {
                                            "type": "t",
                                            "id": 7,
                                            "children": [
                                                {
                                                    "type": "sc",
                                                    "id": 8,
                                                    "children": [
                                                        {
                                                            "type": "p",
                                                            "id": 5,
                                                            "children": [],
                                                            "box": {
                                                                "principal_rect": {
                                                                    "x": 200,
                                                                    "y": 40,
                                                                    "w": 200,
                                                                    "h": 260,
                                                                },
                                                                "margin": {
                                                                    "top": 0,
                                                                    "right": 0,
                                                                    "bottom": 0,
                                                                    "left": 0,
                                                                },
                                                                "border": {
                                                                    "top": 1,
                                                                    "right": 1,
                                                                    "bottom": 1,
                                                                    "left": 1,
                                                                },
                                                                "padding": {
                                                                    "top": 0,
                                                                    "right": 0,
                                                                    "bottom": 0,
                                                                    "left": 0,
                                                                },
                                                            },
                                                        }
                                                    ],
                                                    "axis": "x",
                                                }
                                            ],
                                            "title": "",
                                        },
                                        {
                                            "type": "t",
                                            "id": 9,
                                            "children": [
                                                {
                                                    "type": "sc",
                                                    "id": 10,
                                                    "children": [
                                                        {
                                                            "type": "p",
                                                            "id": 11,
                                                            "children": [],
                                                            "box": {
                                                                "principal_rect": {
                                                                    "x": 200,
                                                                    "y": 40,
                                                                    "w": 200,
                                                                    "h": 260,
                                                                },
                                                                "margin": {
                                                                    "top": 0,
                                                                    "right": 0,
                                                                    "bottom": 0,
                                                                    "left": 0,
                                                                },
                                                                "border": {
                                                                    "top": 1,
                                                                    "right": 1,
                                                                    "bottom": 1,
                                                                    "left": 1,
                                                                },
                                                                "padding": {
                                                                    "top": 0,
                                                                    "right": 0,
                                                                    "bottom": 0,
                                                                    "left": 0,
                                                                },
                                                            },
                                                        }
                                                    ],
                                                    "axis": "x",
                                                }
                                            ],
                                            "title": "",
                                        },
                                    ],
                                    "tab_bar": {
                                        "box": {
                                            "principal_rect": {
                                                "x": 200,
                                                "y": 20,
                                                "w": 200,
                                                "h": 20,
                                            },
                                            "margin": {
                                                "top": 0,
                                                "right": 0,
                                                "bottom": 0,
                                                "left": 0,
                                            },
                                            "border": {
                                                "top": 0,
                                                "right": 0,
                                                "bottom": 0,
                                                "left": 0,
                                            },
                                            "padding": {
                                                "top": 0,
                                                "right": 0,
                                                "bottom": 0,
                                                "left": 0,
                                            },
                                        }
                                    },
                                },
                            ],
                            "axis": "x",
                        }
                    ],
                    "title": "",
                }
            ],
            "tab_bar": {
                "box": {
                    "principal_rect": {"x": 0, "y": 0, "w": 400, "h": 20},
                    "margin": {"top": 0, "right": 0, "bottom": 0, "left": 0},
                    "border": {"top": 0, "right": 0, "bottom": 0, "left": 0},
                    "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0},
                }
            },
        },
    }


def make_tree_state_with_single_window():
    return {
        "width": 400,
        "height": 300,
        "root": {
            "type": "tc",
            "id": 1,
            "children": [
                {
                    "type": "t",
                    "id": 2,
                    "children": [
                        {
                            "type": "sc",
                            "id": 3,
                            "children": [
                                {
                                    "type": "p",
                                    "id": 4,
                                    "children": [],
                                    "box": {
                                        "principal_rect": {
                                            "x": 0,
                                            "y": 20,
                                            "w": 400,
                                            "h": 280,
                                        },
                                        "margin": {
                                            "top": 0,
                                            "right": 0,
                                            "bottom": 0,
                                            "left": 0,
                                        },
                                        "border": {
                                            "top": 1,
                                            "right": 1,
                                            "bottom": 1,
                                            "left": 1,
                                        },
                                        "padding": {
                                            "top": 0,
                                            "right": 0,
                                            "bottom": 0,
                                            "left": 0,
                                        },
                                    },
                                }
                            ],
                            "axis": "x",
                        }
                    ],
                    "title": "",
                }
            ],
            "active_child": 2,
            "tab_bar": {
                "box": {
                    "principal_rect": {"x": 0, "y": 0, "w": 400, "h": 20},
                    "margin": {"top": 0, "right": 0, "bottom": 0, "left": 0},
                    "border": {"top": 0, "right": 0, "bottom": 0, "left": 0},
                    "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0},
                }
            },
        },
    }
