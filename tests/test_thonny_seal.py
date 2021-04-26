"""Test the command-line program to seal the blocks."""
import io
import pathlib
import tempfile
import textwrap
import unittest

import thonnycontrib.thonny_sealed
import thonny_seal.main


class Test_on_valid_examples(unittest.TestCase):
    def test_with_table(self) -> None:
        table = [
            ('', '', 'empty'),
            ('a\nb', 'a\nb', 'No sealing content'),
            (
                textwrap.dedent('''\
                        # sealed: on
                        # sealed: off
                        # sealed: on
                        # sealed: off
                        '''),
                textwrap.dedent('''\
                    # sealed: on 88209294
                    # sealed: off 88209294
                    # sealed: on d09d2eb4
                    # sealed: off d09d2eb4
                    '''),
                "Consecutive sealed blocks"
            ),
            (
                textwrap.dedent('''\
                    some text
                    # sealed: on
                    # sealed: off
                    '''),
                textwrap.dedent('''\
                    some text
                    # sealed: on 88209294
                    # sealed: off 88209294
                    '''),
                "Sealed as suffix"
            ),
            (
                textwrap.dedent('''\
                    # sealed: on
                    # sealed: off
                    some text
                    '''),
                textwrap.dedent('''\
                    # sealed: on 88209294
                    # sealed: off 88209294
                    some text
                    '''),
                "Sealed as prefix"
            ),
            (
                textwrap.dedent('''\
                    prefix
                    # sealed: on
                    # sealed: off
                    suffix
                    '''),
                textwrap.dedent('''\
                    prefix
                    # sealed: on 88209294
                    # sealed: off 88209294
                    suffix
                    '''),
                "Sealed in the middle"
            ),
            (
                textwrap.dedent('''\
                    prefix
                    # sealed: on
                    something sealed
                    # sealed: off
                    suffix
                    '''),
                textwrap.dedent('''\
                    prefix
                    # sealed: on e6b46650
                    something sealed
                    # sealed: off e6b46650
                    suffix
                    '''),
                "Sealed content"
            ),
            (
                textwrap.dedent('''\
                    prefix
                    # sealed: on
                        something sealed
                        # sealed: off
                        suffix
                    '''),
                textwrap.dedent('''\
                    prefix
                    # sealed: on e1d04d89
                        something sealed
                        # sealed: off e1d04d89
                        suffix
                    '''),
                "Indention"
            ),
            (
                textwrap.dedent('''\
                    prefix
                    # sealed: on obsolete
                    something sealed
                    # sealed: off obsolete
                    suffix
                    '''),
                textwrap.dedent('''\
                    prefix
                    # sealed: on e6b46650
                    something sealed
                    # sealed: off e6b46650
                    suffix
                    '''),
                "Obsolete hash updated"
            )
        ]
        for text, expected_text, identifier in table:
            lines = thonnycontrib.thonny_sealed.Lines(text.splitlines())

            got_lines, err = thonny_seal.main.seal(lines=lines)
            self.assertIsNone(err, identifier)
            self.assertIsNotNone(got_lines, identifier)
            assert got_lines is not None

            # We need to split and join again for uniform new-line character over
            # different operating systems.
            self.assertEqual(
                '\n'.join(expected_text.splitlines()), '\n'.join(got_lines), identifier)


class Test_invalid_cases(unittest.TestCase):
    def test_with_table(self) -> None:
        table = [
            (
                textwrap.dedent('''\
                    something
                    # sealed: off
                    '''),
                'Unexpected end of a sealing block at line 2 '
                'without a starting comment.',
                "End without start"
            ),
            (
                textwrap.dedent('''\
                    something
                    # sealed: on
                    '''),
                'Unexpected open block at the end. The block started at line 2.',
                "Start without an end"
            ),
            (
                textwrap.dedent('''\
                    something
                    # sealed: on
                    # sealed: on
                    '''),
                'Unexpected double start of a sealing block at line 3. '
                'The previous block started at line 2.',
                "Double start"
            ),
            (
                textwrap.dedent('''\
                    something
                    # sealed: on   something
                    # sealed: off    else
                    '''),
                "The suffix of the sealing block at line 2 contains "
                "the hash suffix 'something', but the suffix at the end of the block "
                "at line 3 does not match it: 'else'",
                "Unmatched suffix"
            ),
        ]

        for text, expected_error, identifier in table:
            lines = thonnycontrib.thonny_sealed.Lines(text.splitlines())

            got_lines, err = thonny_seal.main.seal(lines=lines)
            self.assertIsNotNone(err, identifier)
            self.assertEqual(expected_error, err)
            self.assertIsNone(got_lines, identifier)


class Test_parsing_of_command_line_arguments(unittest.TestCase):
    def test_path_no_write(self) -> None:
        parser = thonny_seal.main.set_up_parser()
        args = thonny_seal.main.interpret_args(parser.parse_args(args=['--input', 'some/path.py']))

        self.assertEqual(pathlib.Path('some/path.py'), args.input_path)
        self.assertFalse(args.write)

    def test_path_write(self) -> None:
        parser = thonny_seal.main.set_up_parser()
        args = thonny_seal.main.interpret_args(parser.parse_args(
            args=['--input', 'some/path.py', '--write']))

        self.assertEqual(pathlib.Path('some/path.py'), args.input_path)
        self.assertTrue(args.write)


class Test_run(unittest.TestCase):
    def test_no_input_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pth = pathlib.Path(tmpdir) / "some-nonexisting-file.py"

            stdout = io.StringIO()
            stderr = io.StringIO()

            args = thonny_seal.main.Args(input_path=pth, write=False)

            exit_code = thonny_seal.main.run(args=args, stdout=stdout, stderr=stderr)
            self.assertEqual(1, exit_code)

            self.assertEqual('', stdout.getvalue())
            self.assertEqual(f'The input does not exist: {pth}',
                             stderr.getvalue().strip())

    def test_write_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pth = pathlib.Path(tmpdir) / "some-file.py"
            pth.write_text(
                textwrap.dedent(
                    '''\
                    yet
                    # sealed: on
                    another
                    # sealed: off
                    text
                    ''')
            )

            stdout = io.StringIO()
            stderr = io.StringIO()

            args = thonny_seal.main.Args(input_path=pth, write=False)

            exit_code = thonny_seal.main.run(args=args, stdout=stdout, stderr=stderr)
            self.assertEqual(0, exit_code)

            self.assertListEqual(
                textwrap.dedent(
                    '''\
                    yet
                    # sealed: on 034e69ce
                    another
                    # sealed: off 034e69ce
                    text
                    ''').splitlines(),
                stdout.getvalue().splitlines())

            self.assertEqual('', stderr.getvalue())

    def test_write_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pth = pathlib.Path(tmpdir) / "some-file.py"
            pth.write_text(
                textwrap.dedent(
                    '''\
                    yet
                    # sealed: on
                    another
                    # sealed: off
                    text
                    ''')
            )

            stdout = io.StringIO()
            stderr = io.StringIO()

            args = thonny_seal.main.Args(input_path=pth, write=True)

            exit_code = thonny_seal.main.run(args=args, stdout=stdout, stderr=stderr)
            self.assertEqual(0, exit_code)

            got_text = pth.read_text(encoding='utf-8')

            self.assertListEqual(
                textwrap.dedent(
                    '''\
                    yet
                    # sealed: on 034e69ce
                    another
                    # sealed: off 034e69ce
                    text
                    ''').splitlines(),
                got_text.splitlines())

            self.assertEqual('', stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
