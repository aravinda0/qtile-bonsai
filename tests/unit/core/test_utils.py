# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

# ruff: noqa: E501


from qtile_bonsai.core.utils import rewrap


class TestWrap:
    def test_simple_wrap(self):
        text = """The quick brown fox jumped over the lazy dog."""

        rewrapped = rewrap(text, width=30)
        expected = """The quick brown fox jumped
over the lazy dog."""

        assert rewrapped == expected

    def test_leading_whitespace_is_discarded(self):
        text = """    The quick brown fox jumped over the lazy dog."""

        rewrapped = rewrap(text, width=30)
        expected = """The quick brown fox jumped
over the lazy dog."""

        assert rewrapped == expected

    def test_trailing_whitespace_is_discarded(self):
        text = """The quick brown fox jumped over the lazy dog.    """

        rewrapped = rewrap(text, width=30)
        expected = """The quick brown fox jumped
over the lazy dog."""

        assert rewrapped == expected

    def test_lines_ending_with_eos_chars_that_are_below_width_have_newline_preserved(
        self,
    ):
        text = """
The quick brown fox jumped over the lazy dog.

This second paragraph wonders why the dog was labelled as being lazy
when there is no proof of it."""

        rewrapped = rewrap(text, width=90)
        expected = """The quick brown fox jumped over the lazy dog.

This second paragraph wonders why the dog was labelled as being lazy when there is no
proof of it."""

        assert rewrapped == expected

    def test_whitespace_between_sentences_is_preserved(self):
        text = """
The quick brown fox jumped over the lazy dog.



This second paragraph wonders why the dog was labelled as being lazy
when there is no proof of it."""

        rewrapped = rewrap(text, width=90)
        expected = """The quick brown fox jumped over the lazy dog.



This second paragraph wonders why the dog was labelled as being lazy when there is no
proof of it."""

        assert rewrapped == expected

    def test_whitespace_preceding_a_paragraph_is_used_as_indentation_indicator(self):
        text = """
The quick brown fox jumped over the lazy dog.

    This second paragraph wonders why the dog was labelled as being lazy
when there is no proof of it."""

        rewrapped = rewrap(text, width=90)
        expected = """The quick brown fox jumped over the lazy dog.

    This second paragraph wonders why the dog was labelled as being lazy when there is no
    proof of it."""

        assert rewrapped == expected

    def test_with_dedent(self):
        text = """
        The quick brown fox jumped over the lazy dog.

        This second paragraph wonders why the dog was labelled as being lazy
        when there is no proof of it.
        """

        rewrapped = rewrap(text, width=90, dedent=True)
        expected = """The quick brown fox jumped over the lazy dog.

This second paragraph wonders why the dog was labelled as being lazy when there is no
proof of it."""

        assert rewrapped == expected

    def test_with_html_whitespace(self):
        text = """
        The quick brown fox jumped over the lazy dog.

        This second paragraph wonders why the dog was labelled as being lazy
        when there is no proof of it.
        """

        rewrapped = rewrap(text, width=90, html_whitespace=True)
        expected = """The quick brown fox jumped over the lazy dog.<br><br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This second paragraph wonders why the dog was labelled as being lazy when there is<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;no proof of it."""

        assert rewrapped == expected

    def test_different_indentation_levels_across_paragraphs_are_preserved(self):
        text = """
        The quick brown fox jumped over the lazy dog.

        This second paragraph wonders why the dog was labelled as being lazy
        when there is no proof of it.

            This third paragraph reminds everyone to just chill out and not be
            so sensitive about everything.
        """

        rewrapped = rewrap(text, width=90, dedent=True)
        expected = """The quick brown fox jumped over the lazy dog.

This second paragraph wonders why the dog was labelled as being lazy when there is no
proof of it.

    This third paragraph reminds everyone to just chill out and not be so sensitive about
    everything."""

        assert rewrapped == expected

    def test_when_there_is_no_eol_char_ending_input(self):
        text = """
        The quick brown fox jumped over the lazy dog.

        This second paragraph wonders why the dog was labelled as being lazy
        when there is no proof of it.

            This third paragraph reminds everyone to just chill out and not be
            so sensitive about everything
        """

        rewrapped = rewrap(text, width=90, dedent=True)
        expected = """The quick brown fox jumped over the lazy dog.

This second paragraph wonders why the dog was labelled as being lazy when there is no
proof of it.

    This third paragraph reminds everyone to just chill out and not be so sensitive about
    everything"""

        assert rewrapped == expected
