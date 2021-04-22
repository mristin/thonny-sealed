"""Provide common operations used by multiple test modules."""
import collections
import itertools
import tkinter
from typing import Iterable, Tuple, MutableMapping, List, TypeVar

import prettytable

import thonnycontrib.thonny_sealed


def enumerate_with_indices(text_widget: tkinter.Text) -> Iterable[Tuple[str, str]]:
    """Iterate over characters of a text widget."""
    index = '1.0'
    while text_widget.compare(index, '<', tkinter.END):
        yield index, text_widget.get(index)

        index = text_widget.index(f'{index}+1c')


T = TypeVar('T')


def pairwise(iterable: Iterable[T]) -> Iterable[Tuple[T, T]]:
    """"
    Iterate s -> (s0,s1), (s1,s2), (s2, s3), etc.

    From: https://docs.python.org/3/library/itertools.html#itertools-recipes
    """
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def enumerate_with_index_and_tags(
        text_widget: tkinter.Text
) -> Iterable[Tuple[str, str, List[str], List[str]]]:
    """Iterate over (index, character, tag starts, tag ends)."""
    tag_starts = collections.defaultdict(
        lambda: [])  # type: MutableMapping[str, List[str]]

    tag_ends = collections.defaultdict(
        lambda: [])  # type: MutableMapping[str, List[str]]

    for tag_name in text_widget.tag_names():
        for tag_start, tag_end in thonnycontrib.thonny_sealed.each_tag_range(
                text_widget=text_widget, tag_name=tag_name):
            tag_starts[text_widget.index(tag_start)].append(tag_name)
            tag_ends[text_widget.index(tag_end)].append(tag_name)

    for index, character in itertools.chain(
            enumerate_with_indices(text_widget=text_widget), [(tkinter.END, '')]):
        concrete_index = text_widget.index(index)

        yield (
            index,
            character,
            tag_starts.get(concrete_index, []),
            tag_ends.get(concrete_index, [])
        )



def repr_content_and_tags(text_widget: tkinter.Text) -> str:
    """Represent the content, indices and the tag starts and ends as a text table."""
    tbl = prettytable.PrettyTable()
    tbl.field_names = ["Index", "Char", "Tag starts", "Tag ends"]


    for index, character, tag_starts, tag_ends in enumerate_with_index_and_tags(
            text_widget=text_widget):
        tbl.add_row(
            [index, repr(character), ', '.join(tag_starts), ', '.join(tag_ends)])

    tbl.set_style(prettytable.PLAIN_COLUMNS)
    tbl.align = 'l'
    lines = [line.rstrip() for line in tbl.get_string().splitlines()]
    return '\n'.join(lines)
