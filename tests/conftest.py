# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

import pytest

from qtile_bonsai.core.tree import Node, Pane


@pytest.fixture(autouse=True)
def reset_node_id_seq():
    Node.reset_id_seq()
    Pane.min_size = 10
