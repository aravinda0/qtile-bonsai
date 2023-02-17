# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from __future__ import annotations


def validate_unit_range(value: float, field_name: str):
    if not (0 <= value <= 1):
        raise ValueError(f"Value of `{field_name}` must be between 0 and 1 inclusive.")
