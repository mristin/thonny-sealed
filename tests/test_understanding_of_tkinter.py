"""
Test understanding of how to deal with a text widget in Tkinter.

(mristin, 2021-04-11): These were just learning test for me to understand how
text widgets work.
"""
import textwrap
import tkinter
import unittest

import tests.common


class TestIndices(unittest.TestCase):
    def test_empty(self) -> None:
        text_widget = tkinter.Text()

        enumeration = list(
            tests.common.enumerate_with_indices(text_widget=text_widget))

        # A text widget always ends with a new line.
        self.assertListEqual([('1.0', '\n')], enumeration)

    def test_end(self) -> None:
        text_widget = tkinter.Text()
        index = text_widget.index(tkinter.END)
        self.assertEqual('2.0', index)

        char_at_end = text_widget.get(index)

        # Empty char means there is nothing at the end.
        self.assertEqual('', char_at_end)

    def test_one_character(self) -> None:
        text_widget = tkinter.Text()
        text_widget.insert('1.0', 'x')

        enumeration = list(
            tests.common.enumerate_with_indices(text_widget=text_widget))

        self.assertListEqual([('1.0', 'x'), ('1.1', '\n')], enumeration)

    def test_one_character_and_a_new_line(self) -> None:
        text_widget = tkinter.Text()
        text_widget.insert('1.0', 'x\n')

        enumeration = list(
            tests.common.enumerate_with_indices(text_widget=text_widget))

        # Tkinter inserts a new line regardless if it is present or not in the text.
        # The new line in the content is preserved.
        self.assertListEqual([('1.0', 'x'), ('1.1', '\n'), ('2.0', '\n')], enumeration)

    def test_new_line_in_the_middle(self) -> None:
        text_widget = tkinter.Text()
        text_widget.insert('1.0', 'x\ny')

        enumeration = list(
            tests.common.enumerate_with_indices(text_widget=text_widget))

        # The new line in the content is preserved.
        # The new line character in the middle is also indexed.
        self.assertListEqual(
            [('1.0', 'x'), ('1.1', '\n'), ('2.0', 'y'), ('2.1', '\n')],
            enumeration)


class TestDelete(unittest.TestCase):
    def test_empty(self) -> None:
        text_widget = tkinter.Text()
        text_widget.delete('1.0')

        enumeration = list(
            tests.common.enumerate_with_indices(text_widget=text_widget))

        # Tkinter does not allow us to delete the final new-line character.
        self.assertListEqual([('1.0', '\n')], enumeration)

    def test_one_character_with_single_index(self) -> None:
        text_widget = tkinter.Text()
        text_widget.insert('1.0', 'x')

        text_widget.delete('1.0')

        enumeration = list(
            tests.common.enumerate_with_indices(text_widget=text_widget))

        # Tkinter deletes the character, but preserves the final new-line character.
        self.assertListEqual([('1.0', '\n')], enumeration)

    def test_one_character_with_index_range(self) -> None:
        text_widget = tkinter.Text()
        text_widget.insert('1.0', 'x')

        text_widget.delete('1.0', '1.0+1c')

        enumeration = list(
            tests.common.enumerate_with_indices(text_widget=text_widget))

        # Tkinter deletes the character, but preserves the final new-line character.
        self.assertListEqual([('1.0', '\n')], enumeration)

    def test_one_character_in_the_middle_with_index(self) -> None:
        text_widget = tkinter.Text()
        text_widget.insert('1.0', 'xyz')

        # Lines are indexed from 1, columns are indexed from 0!
        text_widget.delete('1.1')

        enumeration = list(
            tests.common.enumerate_with_indices(text_widget=text_widget))

        self.assertListEqual([('1.0', 'x'), ('1.1', 'z'), ('1.2', '\n')], enumeration)

    def test_one_character_in_the_middle_with_index_range(self) -> None:
        text_widget = tkinter.Text()
        text_widget.insert('1.0', 'xyz')

        text_widget.delete('1.1', '1.1+1c')

        enumeration = list(
            tests.common.enumerate_with_indices(text_widget=text_widget))

        self.assertListEqual([('1.0', 'x'), ('1.1', 'z'), ('1.2', '\n')], enumeration)

    def test_two_characters_in_the_middle_with_index_range(self) -> None:
        text_widget = tkinter.Text()
        text_widget.insert('1.0', 'abcd')

        enumeration = list(
            tests.common.enumerate_with_indices(text_widget=text_widget))

        self.assertListEqual(
            [('1.0', 'a'), ('1.1', 'b'), ('1.2', 'c'), ('1.3', 'd'), ('1.4', '\n')],
            enumeration)

        # The start of the range is inclusive, the end of the range is exclusive.
        text_widget.delete('1.1', '1.3')

        enumeration = list(
            tests.common.enumerate_with_indices(text_widget=text_widget))

        self.assertListEqual([('1.0', 'a'), ('1.1', 'd'), ('1.2', '\n')], enumeration)


class TestTags(unittest.TestCase):
    def test_empty_and_no_tags(self) -> None:
        text_widget = tkinter.Text()

        tag_repr = tests.common.repr_content_and_tags(text_widget=text_widget)

        self.assertEqual(
            textwrap.dedent("""\
                Index        Char        Tag starts        Tag ends
                1.0          '\\n'
                end          ''
                 """.rstrip()), tag_repr)

    def test_empty_and_a_tag(self) -> None:
        text_widget = tkinter.Text()
        text_widget.tag_add('my_tag', '1.0', tkinter.END)

        tag_repr = tests.common.repr_content_and_tags(text_widget=text_widget)

        self.assertEqual(
            textwrap.dedent("""\
                Index        Char        Tag starts        Tag ends
                1.0          '\\n'        my_tag
                end          ''                            my_tag
                 """.rstrip()), tag_repr)

    def test_one_character_and_tag_whole_text(self) -> None:
        text_widget = tkinter.Text()
        text_widget.insert('1.0', 'x')
        text_widget.tag_add('my_tag', '1.0', tkinter.END)

        tag_repr = tests.common.repr_content_and_tags(text_widget=text_widget)

        self.assertEqual(
            textwrap.dedent("""\
                Index        Char        Tag starts        Tag ends
                1.0          'x'         my_tag
                1.1          '\\n'
                end          ''                            my_tag
                 """.rstrip()), tag_repr)


class TestInsert(unittest.TestCase):
    def test_insert_on_empty(self) -> None:
        text_widget = tkinter.Text()
        text_widget.insert('1.0', 'x')

        enumeration = list(
            tests.common.enumerate_with_indices(text_widget=text_widget))

        self.assertListEqual([('1.0', 'x'), ('1.1', '\n')], enumeration)

    def test_insert_in_the_middle(self) -> None:
        text_widget = tkinter.Text()
        text_widget.insert('1.0', 'xz')

        text_widget.insert('1.1', 'y')

        enumeration = list(
            tests.common.enumerate_with_indices(text_widget=text_widget))

        # The text is inserted at the position and everything is shifted to the right.
        # The first character at the index corresponds to the first character of the
        # inserted content.
        #
        # The inserts should be hence disallowed at indices:
        # tag start <= index < tag end.
        self.assertListEqual(
            [('1.0', 'x'), ('1.1', 'y'), ('1.2', 'z'), ('1.3', '\n')],
            enumeration)


if __name__ == "__main__":
    unittest.main()
