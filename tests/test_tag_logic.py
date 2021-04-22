"""Test tag operations on ``tkinter.Text`` widget."""
import contextlib
import dataclasses
import os
import pathlib
import tkinter
import unittest
from typing import Iterable, Optional

import hypothesis.strategies
import prettytable
from icontract import snapshot, ensure
import icontract_hypothesis

import tests.common
import thonnycontrib.thonny_sealed


def set_up_text_widget_with_tags(content: str) -> tkinter.Text:
    """Set up the text widget with the content and the tags reset."""
    text_widget = tkinter.Text()
    text_widget.insert('1.0', content)

    errors = thonnycontrib.thonny_sealed.set_tags(text_widget=text_widget)
    if errors:
        errors_str = '\n'.join(f'* {error}' for error in errors)

        # fmt: off
        content_with_lineno = '\n'.join(
            f'{str(i + 1).rjust(3)}: {line}'
            for i, line in enumerate(content.splitlines())
        )
        # fmt: on

        raise AssertionError(
            f"Unexpected errors when setting the tags on the content.\n\n"
            f"The errors were:\n"
            f"{errors_str}\n\n"
            f"The content was:\n{content_with_lineno}"
        )

    return text_widget


def index_range(text_widget: tkinter.Text, start: str, end: str) -> Iterable[str]:
    """Iterate over the indices in the given range."""
    current = text_widget.index(start)
    while text_widget.compare(current, '<', end):
        yield current
        current = text_widget.index(f'{current}+1c')


@dataclasses.dataclass
class TagTestCase:
    path: pathlib.Path
    identifier: str
    content: str


def construct_tags_dir() -> pathlib.Path:
    """Return the path to the directory where the tag test cases reside."""
    this_dir = pathlib.Path(os.path.realpath(__file__)).parent
    tags_dir = this_dir.parent / "test_data" / "tags"
    return tags_dir


def load_test_case(identifier: str) -> TagTestCase:
    """Load a single test case."""
    tags_dir = construct_tags_dir()

    case_dir = tags_dir / identifier
    content = (case_dir / "content.txt").read_text()
    return TagTestCase(path=case_dir, identifier=identifier, content=content)


def iterate_over_tags_test_cases() -> Iterable[TagTestCase]:
    """Iterate over all the ``test_data/tags`` test cases."""
    tags_dir = construct_tags_dir()

    for case_dir in sorted(tags_dir.iterdir()):
        if not case_dir.is_dir():
            continue

        yield load_test_case(identifier=case_dir.name)


class TestTags(unittest.TestCase):
    """Test tag operations on the text widget."""

    # Set to True to re-record the golden files
    record = False

    def test_tags_set(self) -> None:
        for test_case in iterate_over_tags_test_cases():
            text_widget = set_up_text_widget_with_tags(content=test_case.content)
            tags_repr = tests.common.repr_content_and_tags(text_widget=text_widget)

            expected_repr_pth = test_case.path / "tags.txt"

            if TestTags.record:
                expected_repr_pth.write_text(tags_repr)

            expected_repr = expected_repr_pth.read_text()

            self.assertEqual(expected_repr, tags_repr, test_case.identifier)

    def test_is_insertable(self) -> None:
        for test_case in iterate_over_tags_test_cases():
            text_widget = set_up_text_widget_with_tags(content=test_case.content)

            tbl = prettytable.PrettyTable()
            tbl.field_names = [
                'Index',
                'Char',
                "Is insertable '\\nx'",
                "Is insertable 'x\\n'",
                "Is insertable 'x'"]

            tbl.align = 'l'

            for index, char in tests.common.enumerate_with_indices(
                    text_widget=text_widget):
                tbl.add_row(
                    [
                        index,
                        repr(char),
                        thonnycontrib.thonny_sealed.is_insertable(
                            text_widget, index, chars='\nx'),
                        thonnycontrib.thonny_sealed.is_insertable(
                            text_widget, index, chars='x\n'),
                        thonnycontrib.thonny_sealed.is_insertable(
                            text_widget, index, chars='x')
                    ])

            expected_tbl_pth = test_case.path / "is_insertable.txt"

            if TestTags.record:
                expected_tbl_pth.write_text(tbl.get_string())

            expected_tbl = expected_tbl_pth.read_text()
            self.assertEqual(expected_tbl, tbl.get_string())

    def test_is_deletable(self) -> None:
        for test_case in iterate_over_tags_test_cases():
            text_widget = set_up_text_widget_with_tags(content=test_case.content)

            tbl = prettytable.PrettyTable()
            tbl.field_names = [
                'Index',
                'Char',
                "Is deletable"
            ]

            tbl.align = 'l'

            for index, char in tests.common.enumerate_with_indices(
                    text_widget=text_widget):
                tbl.add_row(
                    [
                        index,
                        repr(char),
                        thonnycontrib.thonny_sealed.is_deletable(
                            text_widget, index)
                    ])

            expected_tbl_pth = test_case.path / "is_deletable.txt"

            if TestTags.record:
                expected_tbl_pth.write_text(tbl.get_string())

            expected_tbl = expected_tbl_pth.read_text()
            self.assertEqual(expected_tbl, tbl.get_string())


# fmt: off
@snapshot(
    lambda text_widget:
    thonnycontrib.thonny_sealed.capture_sealed_blocks(text_widget),
    name="sealed_blocks"
)
@snapshot(
    lambda text_widget, index1:
    text_widget.get('1.0', index1),
    name='prefix'
)
@snapshot(
    lambda text_widget, index2:
    text_widget.get(index2, tkinter.END),
    name='suffix'
)
@ensure(
    lambda text_widget, OLD:
    (sealed_blocks := (
            thonnycontrib.thonny_sealed.capture_sealed_blocks(
                text_widget)),
     OLD.sealed_blocks == sealed_blocks
     )
)
@ensure(
    lambda text_widget, index1, OLD:
    text_widget.get('1.0', index1) == OLD.prefix
)
# fmt: on
def naive_delete(text_widget: tkinter.Text, index1: str, index2: str) -> None:
    """Delete all the deletable characters in the range."""
    # Mark the range first, so that the markers shift automatically when we
    # delete the characters
    tag_name = "THONNY_SEALED_TEST_NAIVE_DELETE"
    text_widget.tag_add(tag_name, index1, index2)

    cursor = index1
    tag_range = text_widget.tag_nextrange(tag_name, '1.0')
    if not tag_range:
        return

    end = None  # type: Optional[str]
    start, end = tag_range
    assert start == index1

    while end is not None and text_widget.compare(cursor, '<', end):
        is_deletable = thonnycontrib.thonny_sealed._is_deletable_wo_preconditions(
            text_widget=text_widget, index=cursor
        )

        if is_deletable:
            text_widget.delete(cursor)
        else:
            cursor = text_widget.index(f'{cursor}+1c')

        tag_range = text_widget.tag_nextrange(tag_name, '1.0')
        if tag_range:
            start, end = tag_range
            assert start == index1
        else:
            end = None


class Test_delete_against_a_naive_implementation(unittest.TestCase):
    def test_regression(self) -> None:
        # These are special cases for which we discovered bugs using thorough testing.

        # Do not create ``text_widget1`` and ``text_widget2`` in every loop
        # iteration as this takes too much computational resources unnecessarily
        text_widget1 = tkinter.Text()
        text_widget2 = tkinter.Text()

        for index1, index2, case_id in [
            ('1.0', '4.1', 'newline_seal_newline'),
            ('9.12', '10.1', 'newline_seal_newline')
        ]:
            test_case = load_test_case(identifier=case_id)

            text_widget0 = set_up_text_widget_with_tags(content=test_case.content)

            text_widget1.delete('1.0', tkinter.END)
            text_widget1.insert('1.0', test_case.content)
            thonnycontrib.thonny_sealed.set_tags(text_widget1)

            text_widget2.delete('1.0', tkinter.END)
            text_widget2.insert('1.0', test_case.content)
            thonnycontrib.thonny_sealed.set_tags(text_widget2)

            naive_delete(text_widget1, index1, index2)

            thonnycontrib.thonny_sealed.delete_the_deletables(
                text_widget2,
                index1,
                index2,
                delete_func=lambda start, end: text_widget2.delete(start, end))

            description = (
                f'index1: {index1}, '
                f'index2: {index2}, '
                f'test case: {test_case.identifier}'
            )

            if (
                    text_widget1.get('1.0', tkinter.END)
                    != text_widget2.get('1.0', tkinter.END)
            ):
                tbl0 = prettytable.PrettyTable()
                tbl0.align = 'l'
                tbl0.field_names = ['Index', 'Char', 'Marker']

                deletables = thonnycontrib.thonny_sealed.pin_deletable_ranges(
                    text_widget=text_widget0, index1=index1, index2=index2)

                deletable_starts = [start for start, _ in deletables]
                deletable_ends = [end for _, end in deletables]

                for index in index_range(text_widget0, '1.0', tkinter.END):
                    marker_parts = []
                    if text_widget0.compare(index, '==', index1):
                        marker_parts.append('index1')

                    if text_widget0.compare(index, '==', index2):
                        marker_parts.append('index2')

                    if any(
                            text_widget0.compare(index, '==', start)
                            for start in deletable_starts
                    ):
                        marker_parts.append('deletable_start')

                    if any(
                            text_widget0.compare(index, '==', end)
                            for end in deletable_ends
                    ):
                        marker_parts.append('deletable_end')

                    tbl0.add_row([
                        index, repr(text_widget0.get(index)), ', '.join(marker_parts)])

                print("Original text widget:")
                print(tbl0.get_string())

                tbl1 = prettytable.PrettyTable()
                tbl1.align = 'l'
                tbl1.field_names = ['Index', 'Char']
                for index in index_range(text_widget1, '1.0', tkinter.END):
                    tbl1.add_row([index, repr(text_widget1.get(index))])

                print()
                print("After naive delete:")
                print(tbl1.get_string())

                tbl2 = prettytable.PrettyTable()
                tbl2.align = 'l'
                tbl2.field_names = ['Index', 'Char']
                for index in index_range(text_widget2, '1.0', tkinter.END):
                    tbl2.add_row([index, repr(text_widget2.get(index))])

                print()
                print("After deleting the deletables:")
                print(tbl2.get_string())

            self.assertEqual(
                text_widget1.get('1.0', tkinter.END),
                text_widget2.get('1.0', tkinter.END),
                description
            )

            tag_ranges1 = list(
                thonnycontrib.thonny_sealed.each_tag_range(
                    text_widget1))

            tag_ranges2 = list(
                thonnycontrib.thonny_sealed.each_tag_range(
                    text_widget1))

            self.assertListEqual(tag_ranges1, tag_ranges2, description)

    def test_thoroughly(self) -> None:
        for test_case in iterate_over_tags_test_cases():
            # Set up a text widget so that we can iterate — do not modify it
            text_widget0 = set_up_text_widget_with_tags(
                content=test_case.content)

            # Do not create ``text_widget1`` and ``text_widget2`` in every loop
            # iteration as this takes too much computational resources unnecessarily
            text_widget1 = tkinter.Text()
            text_widget2 = tkinter.Text()

            for index1 in index_range(text_widget0, '1.0', f'{tkinter.END}-1c'):
                # This skip statement is necessary so that we do not waste testing
                # capacity on uninteresting cases.
                if (
                        text_widget0.get(f'{index1}-1c').isalnum()
                        and text_widget0.get(index1).isalnum()
                ):
                    continue

                for index2 in index_range(text_widget0, f'{index1}+1c', tkinter.END):
                    # This skip statement is necessary so that we do not waste testing
                    # capacity on uninteresting cases.
                    if (
                            text_widget0.get(f'{index2}-1c').isalnum()
                            and text_widget0.get(index2).isalnum()
                    ):
                        continue

                    text_widget1.delete('1.0', tkinter.END)
                    text_widget1.insert('1.0', test_case.content)
                    thonnycontrib.thonny_sealed.set_tags(text_widget1)

                    text_widget2.delete('1.0', tkinter.END)
                    text_widget2.insert('1.0', test_case.content)
                    thonnycontrib.thonny_sealed.set_tags(text_widget2)

                    description = (
                        f'index1: {index1}, '
                        f'index2: {index2}, '
                        f'test case: {test_case.identifier}'
                    )

                    try:
                        naive_delete(text_widget1, index1, index2)

                        text_widget2.tag_remove(tkinter.SEL, '1.0', tkinter.END)
                        text_widget2.tag_add(tkinter.SEL, index1, index2)

                        thonnycontrib.thonny_sealed.delete_the_deletables(
                            text_widget2, tkinter.SEL_FIRST, tkinter.SEL_LAST,
                            lambda start, end: text_widget2.delete(start, end))
                    except Exception as err:
                        raise AssertionError(
                            f"The following input caused an exception: {description}"
                        ) from err

                    self.assertEqual(
                        text_widget1.get('1.0', tkinter.END),
                        text_widget2.get('1.0', tkinter.END),
                        description
                    )

                    tag_ranges1 = list(
                        thonnycontrib.thonny_sealed.each_tag_range(
                            text_widget1))

                    tag_ranges2 = list(
                        thonnycontrib.thonny_sealed.each_tag_range(
                            text_widget1))

                    self.assertListEqual(tag_ranges1, tag_ranges2, description)


class Test_with_icontract_hypothesis(unittest.TestCase):
    lines_strategy = icontract_hypothesis.infer_strategy(
        thonnycontrib.thonny_sealed.assert_lines
    ).map(lambda d: thonnycontrib.thonny_sealed.assert_lines(**d))

    hypothesis.strategies.register_type_strategy(
        thonnycontrib.thonny_sealed.Lines,  # type: ignore
        lines_strategy
    )

    def test_extract_markers(self) -> None:
        icontract_hypothesis.test_with_inferred_strategy(
            thonnycontrib.thonny_sealed.extract_markers
        )

    def test_parse_blocks(self) -> None:
        icontract_hypothesis.test_with_inferred_strategy(
            thonnycontrib.thonny_sealed.parse_blocks
        )


if __name__ == "__main__":
    unittest.main()
