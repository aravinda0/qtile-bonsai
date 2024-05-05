# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from __future__ import annotations

import re
import textwrap


def validate_unit_range(value: float, field_name: str):
    if not (0 <= value <= 1):
        raise ValueError(f"Value of `{field_name}` must be between 0 and 1 inclusive.")


def all_or_none(*args, err_hint: str | None = None):
    nulls = [x is None for x in args]
    if all(nulls) or not any(nulls):
        return args

    err_hint = err_hint or "The variables"
    raise ValueError(f"{err_hint} must all be provided or all be `None`")


def rewrap(
    text: str, width: int = 90, *, dedent: bool = False, html_whitespace: bool = False
) -> str:
    """Rewraps text at the requested width, while preserving whitespace
    (newlines/indentation) that are apparently intentional.

    For example, newlines after 'end of sentence' characters such as `.` or `:`
    are preserved and the sentence doesn't get combined with the subsequent
    sentence for wrapping.

    Sentences are otherwise (re)wrapped at the requested width.
    If a sentence is preceded by some whitespace, it is used for the basis for
    indentation during wrapping.

    The leading and trailing whitespace around the input string is discarded.

    Args:
        text:
            The input string. It will be stripped of leading and trailing
            spaces.
        width:
            The width for wrapping.
            This a bit different then `textwrap.wrap()`. Wrapping happens in the
            context of each paragraph. If a paragraph has been indented in the
            source string, that indentation is preserved.
            So basically, any whitespace preceding a paragraph is a request to
            maintain indentation.
        dedent:
            If `True`, the input string will first have `textwrap.dedent()`
            invoked on it.
        html_whitespace:
            If `True`, indentation is preserved by replacing all whitespace with
            `&nbsp` and newlines are replaced with `<br>`.
    """
    if dedent:
        text = textwrap.dedent(text)

    # Strip after any dedenting so we don't wipe leading indent and bork
    # dedent's calculations.
    text = text.strip()

    eos_chars_re = r"[\.:!?`\)]"
    pattern = rf"(?P<leading_ws>\s*?\n?)(?P<indent> *)(?P<line>\S.*?(?:{eos_chars_re} *|$))(?P<trailing_ws>\n|$)"  # noqa: E501

    out_lines = []
    matches = re.findall(pattern, text, flags=re.DOTALL)
    for m in matches:
        leading_ws, indent, line, trailing_ws = m

        # Get rid of extraneous spaces in between. These will usually be due to
        # pre-existing wrapping.
        line = re.sub(r"\s+", " ", line)

        line = "\n".join(
            textwrap.wrap(
                line, width=width, initial_indent=indent, subsequent_indent=indent
            )
        )
        line = f"{leading_ws}{line}{trailing_ws}"

        if html_whitespace:
            line = re.sub(r"^ +", _replace_with_hard_space, line, flags=re.MULTILINE)
            line = re.sub(r"\n", "<br>", line)

        out_lines.append(line)

    return "".join(out_lines)


def _replace_with_hard_space(match):
    return len(match.group(0)) * "&nbsp;"


def to_snake_case(name: str) -> str:
    """Convert the provided string to snake case.

    Stolen from https://stackoverflow.com/a/46493824
    """
    words = re.findall(r"[A-Z]?[a-z]+|[A-Z]{2,}(?=[A-Z][a-z]|\d|\W|$)|\d+", name)
    return "_".join(map(str.lower, words))
