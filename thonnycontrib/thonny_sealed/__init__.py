"""Automatically test Python code using CrossHair in Thonny."""
import abc
import hashlib
import re
import tkinter.messagebox
from _tkinter import Tcl_Obj
from typing import (
    List,
    Optional,
    Tuple,
    Iterable,
    TypeVar,
    Callable,
    Sequence,
    Union,
    overload,
    cast,
)

import icontract
from icontract import require, ensure, DBC
import thonny
import thonny.codeview
import thonny.workbench

name = "thonny-sealed"  # pylint: disable=invalid-name

# From: https://github.com/Franccisco/thonny-black-code-format/blob/master/thonnycontrib/thonny_black_format/__init__.py
# Temporary fix: this function comes from thonny.running, but importing that
# module may conflict with outdated Thonny installations from some Linux
# repositories.
_console_allocated = False  # pylint: disable=invalid-name

TAG_NAME = "thonny_sealed"

T = TypeVar("T")  # pylint: disable=invalid-name


def each_tag_range(
    text_widget: tkinter.Text, tag_name: str = TAG_NAME
) -> Iterable[Tuple[Tcl_Obj, Tcl_Obj]]:
    """Iterate over (start, end) for the given tags."""
    tag_ranges = text_widget.tag_ranges(tag_name)
    if tag_ranges:
        assert len(tag_ranges) % 2 == 0
        for i in range(0, len(tag_ranges), 2):
            assert text_widget.compare(tag_ranges[i], "<", tag_ranges[i + 1])
            yield tag_ranges[i], tag_ranges[i + 1]


def check_tags(text_widget: tkinter.Text) -> Optional[str]:
    """
    Check the sealing tags.

    Return error message, if any.
    """
    prev_start = None
    prev_end = None
    for start, end in each_tag_range(text_widget):
        if text_widget.compare(start, ">=", end):
            return f"The tag {TAG_NAME!r} is invalid: start >= end: {(start, end)}"

        if prev_start is not None:
            assert prev_end is not None

            if text_widget.compare(prev_start, ">=", start) or text_widget.compare(
                prev_end, ">", start
            ):
                return (
                    f"The tag {TAG_NAME!r} for range {(prev_start, prev_end)} "
                    f"is invalid: it overlaps the next range {(start, end)}"
                )

        first_line = text_widget.get(f"{start} linestart", f"{start} lineend")
        if not COMMENT_FIRST_RE.match(first_line):
            return (
                f"The first line of the tag {TAG_NAME!r} for range {(start, end)} "
                f"is invalid: expected it to match {COMMENT_FIRST_RE.pattern}, "
                f"but got: {first_line!r}"
            )

        last_line = text_widget.get(f"{end} linestart", f"{end} lineend")
        if not COMMENT_LAST_RE.match(last_line):
            return (
                f"The last line of the tag {TAG_NAME!r} for range {(start, end)} "
                f"is invalid: expected it to match {COMMENT_LAST_RE.pattern}, "
                f"but got: {last_line!r}"
            )

        # A sealed block should either start at the beginning of the content
        # or be preceded by a new line.
        if text_widget.compare(start, ">", "1.0"):
            prev_char = text_widget.get(f"{start}-1c")
            if prev_char != "\n":
                return (
                    f"Expected a new-line character ('\\n') to precede a sealed block "
                    f"corresponding to the tag {TAG_NAME!r} "
                    f"in the range ({start, end}), "
                    f"but the preceding character was: {prev_char!r}"
                )

        # The new line must not be included in the tag, otherwise tkinter will merge
        # the consecutive tags together!
        if text_widget.get(end) != "\n":
            return (
                f"The tag {TAG_NAME!r} for range {(start, end)} is invalid: "
                f"expected a '\\n' at the end the tag ({end}), "
                f"but got: {text_widget.get(end)}; "
                f"the text of the tag is: {text_widget.get(start, end)!r}"
            )

        prev_start = start
        prev_end = end

    return None


# fmt: off
@require(
    lambda text_widget:
    check_tags(text_widget) is None,
    enabled=icontract.SLOW
)
@ensure(
    lambda result, chars:
    not (len(chars) == 0) or result
)
# fmt: on
def is_insertable(text_widget: tkinter.Text, index: str, chars: str) -> bool:
    """Return True if the ``chars`` can be inserted at ``index``."""
    if len(chars) == 0:
        return True

    prevrange = text_widget.tag_prevrange(TAG_NAME, index)
    if prevrange:
        start, end = prevrange
        assert text_widget.compare(start, "<", index), "Expected tag_prevrange behavior"

        if text_widget.compare(index, "==", end):
            # We can add a new line + more text just after the sealed block,
            # but not a character as that would disfigure the sealing comment.
            return chars.startswith("\n")

        elif text_widget.compare(index, "<=", end):
            return False

        else:
            assert text_widget.compare(index, ">", end), "Expected default case"
            pass

    nextrange = text_widget.tag_nextrange(TAG_NAME, index)
    if nextrange:
        start, end = nextrange
        assert text_widget.compare(
            index, "<=", start
        ), "Expected tag_nextrange behavior"

        if text_widget.compare(index, "==", start):
            # We can add some text + a new line just before the sealed block,
            # but no text not ending in a new line as that would disfigure
            # the sealing comment.
            return chars.endswith("\n")

        else:
            assert text_widget.compare(index, "<", start)
            return True

    return True


# fmt: off
@require(
    lambda text_widget:
    check_tags(text_widget) is None,
    enabled=icontract.SLOW
)
# fmt: on
def is_deletable(text_widget: tkinter.Text, index: str) -> bool:
    """Return True if the character at ``index`` can be deleted."""
    return _is_deletable_wo_preconditions(text_widget, index)


def _is_deletable_wo_preconditions(text_widget: tkinter.Text, index: str) -> bool:
    """Implement ``is_deletable`` without contracts to allow for the naive algorithm."""
    prevrange = text_widget.tag_prevrange(TAG_NAME, index)
    if prevrange:
        start, end = prevrange
        assert text_widget.compare(start, "<", index), "Expected tag_prevrange behavior"

        # We check for '<=' instead of '<' to make sure that the new line
        # just after the end can not be deleted either.
        if text_widget.compare(index, "<=", end):
            return False

    nextrange = text_widget.tag_nextrange(TAG_NAME, index)
    if nextrange:
        start, end = nextrange
        assert text_widget.compare(
            index, "<=", start
        ), "Expected tag_nextrange behavior"

        # Index hits exactly the start of the sealed block.
        if text_widget.compare(index, "==", start):
            return False

        # We have to make sure that we do not delete the new-line *before* the
        # start of the sealed block. If we do, the comment would not be on an isolated
        # line anymore.
        if text_widget.compare(f"{index}+1c", "==", start):
            if text_widget.compare(index, "==", "1.0"):
                # Putting the sealed block at the beginning of the text is OK.
                return True

            char_at_index = text_widget.get(index)
            assert char_at_index == "\n", (
                f"Expected a new-line at index {index} "
                f"*before* a sealed block {(start, end)}, "
                f"but got: {char_at_index}"
            )

            prev_char = text_widget.get(f"{index}-1c")

            # It's OK to delete a new-line character if the preceding character is also
            # a new line.
            return prev_char == "\n"

        assert text_widget.compare(index, "<", start), "Expected default case"
        return True

    return True


def pairwise(iterable: Iterable[T]) -> Iterable[Tuple[T, T]]:
    """
    Iterate over ``(s0, s1, s2, ...)`` as ``((s0, s1), (s1, s2), ...)``.

    >>> list(pairwise([]))
    []

    >>> list(pairwise([1]))
    []

    >>> list(pairwise([1, 2]))
    [(1, 2)]

    >>> list(pairwise([1, 2, 3]))
    [(1, 2), (2, 3)]
    """
    previous = None  # type: Optional[T]
    for current in iterable:
        if previous is not None:
            yield previous, current

        previous = current


# fmt: off
@require(
    lambda index1, index2:
    index1 != '' and index2 != ''
)
@require(
    lambda text_widget, index1, index2:
    text_widget.compare(index1, '<', index2),
    "Query interval valid"
)
@require(
    lambda text_widget:
    check_tags(text_widget) is None
)
@ensure(
    lambda text_widget, index1, index2, result:
    all(
        text_widget.compare(start, '>=', index1)
        and text_widget.compare(end, '<=', index2)
        for start, end in result
    ),
    "Deletable ranges within the query interval"
)
@ensure(
    lambda text_widget, result:
    all(
        text_widget.compare(prev_end, '<=', start)
        for (_, prev_end), (start, _) in pairwise(result)
    ),
    "Deletable ranges do not overlap"
)
@ensure(
    lambda text_widget, result:
    all(
        text_widget.compare(start, '<', end)
        for start, end in result
    ),
    "Valid deletable ranges"
)
# fmt: on
def pin_deletable_ranges(
    text_widget: tkinter.Text, index1: str, index2: str
) -> List[Tuple[str, str]]:
    """Determine the ranges in ``(index1, index2)`` which can be deleted."""
    pass  # for pydocstyle

    # Handle the simple case first where only a single character has been selected
    if text_widget.compare(index2, "==", f"{index1}+1c"):
        if is_deletable(text_widget, index=index1):
            return [(index1, index2)]
        else:
            return []

    candidate_start = index1

    prevrange = text_widget.tag_prevrange(TAG_NAME, index1)
    if prevrange:
        start, end = prevrange
        assert text_widget.compare(
            start, "<", index1
        ), "Expected tag_prevrange behavior"

        char_at_end = text_widget.get(end)
        assert char_at_end == "\n", (
            f"Expected the tag {TAG_NAME} in range {(start, end)} "
            f"to have a new-line character at end ({end}), "
            f"but got: {char_at_end!r}"
        )

        # If ``end`` is past ``index2``, the whole selection is within a sealed block
        # as ``start < index1``.
        #
        # The ``index2`` is exclusive, so we need to check for ``end+1`` as ``end``
        # points to a new-line character.
        if text_widget.compare(index2, "<=", f"{end}+1c"):
            return []

        if text_widget.compare(index1, "<=", end):
            # The start of the interval, ``index1``, hits the sealed block.
            #
            # We must not delete the new-line character just after the sealed block
            # in order to preserve the last sealing line.
            candidate_start = text_widget.index(f"{end}+1c")

    result = []  # type: List[Tuple[str, str]]
    while text_widget.compare(candidate_start, "<", index2):
        old_candidate_start = candidate_start

        nextrange = text_widget.tag_nextrange(TAG_NAME, candidate_start)
        if not nextrange:
            # There is no sealed block from the ``candidate_start`` till the end of
            # the content, so it's safe to delete whatever we want.
            result.append((candidate_start, index2))
            candidate_start = index2  # Exit the loop

        else:
            start, end = nextrange
            assert text_widget.compare(
                candidate_start, "<=", start
            ), "Expected tag_nextrange behavior"

            if text_widget.compare(candidate_start, "==", start):
                # The candidate_start hits exactly the beginning of the sealed block.
                # We can only move the ``candidate_start`` to the next position,
                # but there is no deletable to be added to the ``result``.
                pass

            elif text_widget.compare(candidate_start, "<", start):
                # We can add the deletable till the sealed block.

                if text_widget.compare(index2, "<", start):
                    result.append((candidate_start, index2))
                else:
                    # We have to be careful that we do not delete the new-line character
                    # just before the sealed block as it might disfigure the first line
                    # of the following sealed block.

                    # The prefix of a sealed block needs to be deleted. This is OK
                    # as it will move the sealed block all the way to the beginning
                    # of the content maintaining the lines.
                    if text_widget.compare(candidate_start, "==", "1.0"):
                        result.append((candidate_start, start))

                    # If the new-line character is preceding ``candidate_start``, it is
                    # OK to delete the line just before the sealed block as
                    # the sealing lines will be still maintained after the deletion.
                    elif text_widget.get(f"{candidate_start}-1c") == "\n":
                        result.append((candidate_start, start))

                    # We need to leave out the new-line just before the sealed block
                    # in order to maintain the sealing line.
                    else:
                        # Consider only real, non-empty ranges
                        candidate_end = text_widget.index(f"{start}-1c")
                        if text_widget.compare(candidate_start, "<", candidate_end):
                            result.append((candidate_start, candidate_end))
            else:
                raise AssertionError(
                    f"Unexpected case: "
                    f"candidate_start == {candidate_start},"
                    f"start == {start}"
                )

            ##
            # Move the ``candidate_start`` to the next position
            ##

            char_at_end = text_widget.get(end)
            assert char_at_end == "\n", (
                f"Expected a new-line character at end "
                f"of a {TAG_NAME!r} tag in range {(start, end)}, "
                f"but got: {char_at_end}"
            )

            # We need to move the deletable past the new-line character at the
            # end of the sealed block to maintain the last sealed line.
            candidate_start = text_widget.index(f"{end}+1c")

        assert text_widget.compare(old_candidate_start, "<", candidate_start), (
            f"Loop invariant must hold, but: "
            f"old_candidate_start is {old_candidate_start}, "
            f"candidate_start is {candidate_start}"
        )

    return result


COMMENT_FIRST_RE = re.compile(
    r"^"
    r"(?P<prefix>\s*#\s*(sealed|Sealed|SEALED)\s*(:|\s)\s*(on|On|ON))"
    r"(?P<suffix>(\s*|\s+.*))?$"
)

COMMENT_LAST_RE = re.compile(
    r"^"
    r"(?P<prefix>\s*#\s*(sealed|Sealed|SEALED)\s*(:|\s)\s*(off|Off|OFF))"
    r"(?P<suffix>(\s*|\s+.*))?$"
)


class SealMarker(DBC):
    """Represent the start or an end of a block."""

    # fmt: off
    @require(
        lambda lineno:
        lineno >= 0
    )
    @require(
        lambda prefix:
        len(prefix) > 0
    )
    @require(
        lambda suffix:
        suffix is None or suffix.strip() == suffix
    )
    # fmt: on
    def __init__(self, lineno: int, prefix: str, suffix: Optional[str]) -> None:
        """Initialize with the given values."""
        self.lineno = lineno
        self.prefix = prefix
        self.suffix = suffix


class First(SealMarker):
    """Represent the start of a sealed block."""


class Last(SealMarker):
    """Represent the end of a sealed block."""


class Lines(DBC, Sequence[str]):
    """Represent a sequence of text lines."""

    # fmt: off
    @require(
        lambda lines:
        all('\n' not in line and '\r' not in line for line in lines)
    )
    # fmt: on
    def __new__(cls, lines: Sequence[str]) -> "Lines":
        r"""
        Ensure the properties on the ``lines``.

        Please make sure that you transfer the "ownership" immediately to Lines
        and don't modify the original list of strings any more:

        .. code-block: python

            ##
            # OK
            ##

            lines = Lines(some_text.splitlines())

            ##
            # Not OK
            ##

            some_lines = some_text.splitlines()
            lines = Lines(some_lines)
            # ... do something assuming ``lines`` is immutable ...

            some_lines[0] = "This will break \n your logic"
            # ERROR! lines[0] now contains a new-line which is not what you'd
            # expect!

        """
        return cast(Lines, lines)

    def __add__(self, other: "Lines") -> "Lines":
        """Concatenate two list of lines."""
        raise NotImplementedError("Only for type annotations")

    # pylint: disable=function-redefined

    @overload
    def __getitem__(self, index: int) -> str:
        """Get the item at the given integer index."""
        pass

    @overload
    def __getitem__(self, index: slice) -> "Lines":
        """Get the slice of the lines."""
        pass

    def __getitem__(self, index: Union[int, slice]) -> Union[str, "Lines"]:
        """Get the line(s) at the given index."""
        raise NotImplementedError("Only for type annotations")

    def __len__(self) -> int:
        """Return the number of the lines."""
        raise NotImplementedError("Only for type annotations")


# fmt: off
@ensure(
    lambda lines, result:
    len(result) <= len(lines),
    "Not more markers than lines by the pigeonhole principle"
)
# fmt: on
def extract_markers(lines: Lines) -> List[SealMarker]:
    """Go over lines and extract the markers."""
    result = []  # type: List[SealMarker]

    for i, line in enumerate(lines):
        mtch = COMMENT_FIRST_RE.match(line)
        if mtch:
            result.append(
                First(
                    lineno=i,
                    prefix=mtch.group("prefix"),
                    suffix=(
                        None
                        if mtch.group("suffix") is None
                        else mtch.group("suffix").strip()
                    ),
                )
            )
            continue

        mtch = COMMENT_LAST_RE.match(line)
        if mtch is not None:
            result.append(
                Last(
                    lineno=i,
                    prefix=mtch.group("prefix"),
                    suffix=(
                        None
                        if mtch.group("suffix") is None
                        else mtch.group("suffix").strip()
                    ),
                )
            )
            continue

    return result


class Block:
    """Represent a sealed block."""

    # fmt: off
    @require(
        lambda first, last:
        first.suffix.strip() == last.suffix.strip()
    )
    @require(
        lambda first, last:
        first.lineno < last.lineno
    )
    # fmt: on
    def __init__(self, first: First, last: Last) -> None:
        """Initialize with the given values."""
        self.first = first
        self.last = last


# fmt: off
@ensure(
    lambda result:
    not (result[1] is None)
    or all(
        prev.last.lineno < current.first.lineno
        for prev, current in pairwise(result[0])
    ),
    "Blocks non-overlapping"
)
@ensure(
    lambda markers, result:
    not (result[1] is None) or len(result[0]) <= len(markers) / 2,
    "Not too many blocks"
)
@ensure(
    lambda result:
    (result[0] is None) ^ (result[1] is None)
)
# fmt: on
def parse_blocks(
    markers: Sequence[SealMarker],
) -> Tuple[Optional[List[Block]], Optional[str]]:
    """
    Parse the blocks from the given markers.

    We verify here that the suffixes between the start and the end match, but not that
    they correspond to the content.

    Double starts and no closing comments are reported as well.

    Return (list of blocks, error if any).
    """
    result = []  # type: List[Block]

    first = None  # type: Optional[First]
    for marker in markers:
        if isinstance(marker, First):
            if first is None:
                first = marker
            else:
                return (
                    None,
                    f"Unexpected double start of a sealing block "
                    f"at line {marker.lineno + 1}. "
                    f"The previous block started at line {first.lineno + 1}.",
                )

        if isinstance(marker, Last):
            if first is None:
                return (
                    None,
                    f"Unexpected end of a sealing block at line {marker.lineno + 1} "
                    f"without a starting comment.",
                )

            assert first is not None

            if first.suffix is None and marker.suffix is not None:
                return (
                    None,
                    f"The suffix of the sealing block at line {first.lineno + 1} "
                    f"contains no hash suffix, "
                    f"but the hash suffix of the block at line {marker.lineno + 1} "
                    f"is: {marker.suffix!r}",
                )

            elif first.suffix is not None and marker.suffix is None:
                return (
                    None,
                    f"The suffix of the sealing block at line {first.lineno + 1} "
                    f"contains the hash suffix {first.suffix!r}, "
                    f"but there is no suffix at the end of the block "
                    f"at line {marker.lineno + 1}.",
                )
            else:
                assert first.suffix is not None
                assert marker.suffix is not None

                if first.suffix != marker.suffix:
                    return (
                        None,
                        f"The suffix of the sealing block at line {first.lineno + 1} "
                        f"contains the hash suffix {first.suffix!r}, but the suffix "
                        f"at the end of the block at line {marker.lineno + 1} "
                        f"does not match it: {marker.suffix!r}",
                    )

            result.append(Block(first=first, last=marker))
            first = None

    if first is not None:
        return (
            None,
            f"Unexpected open block at the end. "
            f"The block started at line {first.lineno + 1}.",
        )

    return result, None


# fmt: off
@require(
    lambda lines, blocks:
    all(
        0 <= block.first.lineno < len(lines)
        and 0 <= block.last.lineno < len(lines)
        for block in blocks
    ),
    "Block line ranges valid"
)
@require(
    lambda blocks:
    all(
        prev.last.lineno < current.first.lineno
        for prev, current in pairwise(blocks)
    ),
    "Blocks non-overlapping"
)
# fmt: on
def verify_blocks(
    lines: Lines, blocks: Sequence[Block]
) -> Tuple[List[Block], List[str]]:
    """
    Verify that the hashes of the sealed blocks are valid.

    Return (good blocks, errors if any).
    """
    ok_blocks = []  # type: List[Block]
    errors = []  # type: List[str]

    matched_blocks = 0
    for block in blocks:
        content = "\n".join(lines[block.first.lineno + 1 : block.last.lineno])

        # Go over all possible block indices in case the user copy/pasted a block
        matched = False
        for i in range(matched_blocks, len(blocks)):
            content_to_seal = f"{i}.{content}"
            md5hex = hashlib.md5(content_to_seal.encode("utf-8")).hexdigest()
            truncated_md5 = md5hex[-8:]

            got_hash = (
                block.first.suffix.strip() if block.first.suffix is not None else ""
            )

            if truncated_md5 != got_hash:
                continue
            else:
                matched = True
                matched_blocks += 1
                ok_blocks.append(block)

        if not matched:
            errors.append(
                f"The hash of the sealed block starting "
                f"at line {block.first.lineno + 1} is invalid. "
                f"Did you seal the content of the file properly with thonny-seal?"
            )

    return ok_blocks, errors


# fmt: off
@require(
    lambda text_widget:
    not text_widget.tag_ranges(TAG_NAME),
    f"Tags for {TAG_NAME!r} must be deleted before setting the new tags")
@ensure(
    lambda text_widget:
    check_tags(text_widget) is None)
# fmt: on
def set_tags(text_widget: tkinter.Text) -> List[str]:
    """
    Reset the tags corresponding to the sealed content.

    Return the list of errors, if any.
    """
    lines = Lines(text_widget.get("1.0", tkinter.END).splitlines())

    markers = extract_markers(lines=lines)

    blocks, error = parse_blocks(markers=markers)
    if error is not None:
        return [error]

    assert blocks is not None
    ok_blocks, errors = verify_blocks(lines=lines, blocks=blocks)
    if errors:
        return errors

    for block in ok_blocks:
        # The tag start is inclusive, the tag end is exclusive.
        # The new line at the end of the sealed area is excluded since
        # tkinter automatically merges the consecutive tags. However, we want
        # to avoid this behavior as we need to consider sealed blocks
        # in isolation.
        #
        # Note that this new line at the end needs to be handled with care
        # so that the comments are not disfigured!
        tag_start = f"{block.first.lineno + 1}.0"
        tag_end = f"{block.last.lineno + 1}.{len(lines[block.last.lineno])}"

        text_widget.tag_add(TAG_NAME, tag_start, tag_end)

    return []


def set_seal_appearance(text_widget: tkinter.Text) -> None:
    """Set the appearance of the sealed blocks."""
    text_widget.tag_config(TAG_NAME, background="lightgrey")


# fmt: off
@require(
    lambda text_widget:
    check_tags(text_widget) is None
)
# fmt: on
def capture_sealed_blocks(text_widget: tkinter.Text) -> List[str]:
    """Capture the content of the sealed blocks."""
    result = []  # type: List[str]
    for start, end in each_tag_range(text_widget=text_widget):
        content = text_widget.get(start, end)
        result.append(content)

    return result


# fmt: off
@require(
    lambda text_widget:
    check_tags(text_widget) is None
)
@require(
    lambda text_widget, index1, index2:
    text_widget.compare(index1, '<', index2)
)
# fmt: on
def delete_the_deletables(
    text_widget: tkinter.Text,
    index1: str,
    index2: str,
    delete_func: Callable[[str, str], None],
) -> None:
    """
    Delete the deletable content in the given range ``(index1, index2)``.

    The sealed blocks in the range are preserved.
    """
    deletables = pin_deletable_ranges(
        text_widget=text_widget, index1=index1, index2=index2
    )

    tag_name = "THONNY_SEALED_DELETE_THE_DELETABLES"

    for start, end in deletables:
        text_widget.tag_add(tag_name, start, end)

    while True:
        tag_range = text_widget.tag_nextrange(tag_name, "1.0")
        if not tag_range:
            break

        start, end = tag_range
        delete_func(start, end)


def patch_code_view() -> None:
    """Patch the ``thonny.codeview.CodeView`` and ``CodeViewText``."""
    old_set_content = thonny.codeview.CodeView.set_content

    def set_content(
        self: thonny.codeview.CodeView, content: str, keep_undo: bool = False
    ) -> None:
        """Patch ``set_content`` to set the tags after the content update."""
        assert isinstance(self.text, tkinter.Text)
        assert isinstance(content, str)

        self.text.tag_delete(TAG_NAME)
        old_set_content(self, content, keep_undo)
        errors = set_tags(text_widget=self.text)
        if errors:
            tkinter.messagebox.showwarning(
                title="Broken seals",
                message=(
                    "One or more sealed blocks have been broken in the file:\n"
                    "\n".join(errors)
                ),
            )

        set_seal_appearance(text_widget=self.text)

    thonny.codeview.CodeView.set_content = set_content

    old_intercept_insert = thonny.codeview.CodeViewText.intercept_insert

    def intercept_insert(  # type: ignore
        self: thonny.codeview.CodeViewText, index: str, chars: str, tags=None, **kw
    ) -> None:
        """Wrap ``intercept_insert`` to ignore inserts in the sealed areas."""
        if is_insertable(text_widget=self, index=index, chars=chars):
            old_intercept_insert(self, index, chars, tags, **kw)
        else:
            self.bell()

    thonny.codeview.CodeViewText.intercept_insert = intercept_insert

    # The function ``intercept_delete`` did not behave correctly when applied on
    # the selection + paste command. The paste was simply executed.
    #
    # In contract, ``direct_delete`` was respected.
    old_direct_delete = thonny.codeview.CodeViewText.direct_delete

    def direct_delete(  # type: ignore
        self: thonny.codeview.CodeViewText, index1, index2=None, **kw
    ) -> None:
        """Wrap ``direct_delete`` to ignore deletes in the sealed areas."""
        if index2 is None:
            if is_deletable(text_widget=self, index=index1):
                old_direct_delete(self, index1, index2, **kw)
            else:
                self.bell()
        else:
            delete_the_deletables(
                text_widget=self,
                index1=index1,
                index2=index2,
                delete_func=(
                    lambda start, end: old_direct_delete(  # type: ignore
                        self, start, end
                    )
                ),
            )

    thonny.codeview.CodeViewText.direct_delete = direct_delete


def load_plugin() -> None:
    """Load the plug-in in Thonny."""
    # pylint: disable=unused-argument
    patch_code_view()
