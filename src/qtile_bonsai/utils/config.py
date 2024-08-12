# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


import dataclasses
from typing import Any, Callable, ClassVar


@dataclasses.dataclass
class ConfigOption:
    UNSET: ClassVar[object] = object()

    name: str
    default_value: Any
    description: str
    validator: Callable[[str, Any], tuple[bool, str | None]] | None = None

    # This is just a documentation helper. To allow us to present enum values such as
    # `Gruvbox.bright_red` as the friendly enum string instead of a cryptic `#fb4934`.
    default_value_label: str | None = None
