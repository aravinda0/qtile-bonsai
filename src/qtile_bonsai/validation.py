# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from typing import Any


def validate_border_size(key: str, value: Any) -> tuple[bool, str | None]:
    if not isinstance(value, int):
        err_msg = (
            f"{key} can only accept a single integer that is applicable to all sides."
        )
        return (False, err_msg)
    return (True, None)


def validate_default_add_mode(key: str, value: Any) -> tuple[bool, str | None]:
    allowed_values = ["tab", "split_x", "split_y", "match_previous"]
    if value not in allowed_values and not callable(value):
        err_msg = f"{key} can only be one of {allowed_values}, or a callable."
        return (False, err_msg)
    return (True, None)
