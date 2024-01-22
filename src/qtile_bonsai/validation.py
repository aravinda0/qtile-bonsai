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
