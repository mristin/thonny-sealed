"""Seal the content of the sealed blocks by hashing their content."""

import argparse
import hashlib
import pathlib
import shutil
import sys
import uuid
from typing import Tuple, Optional, TextIO, List

from icontract import ensure

import thonnycontrib.thonny_sealed


def set_up_parser() -> argparse.ArgumentParser:
    """Create the parser for the command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        help="path to the input file that needs to be sealed",
        type=str,
        required=True,
    )
    parser.add_argument(
        "-w",
        "--write",
        help=(
            "If set, overwrite the content of the file in-place. "
            "Otherwise the sealed file is written to STDOUT."
        ),
        action="store_true",
    )
    return parser


class Args:
    """Represent parsed program arguments."""

    def __init__(self, input_path: pathlib.Path, write: bool) -> None:
        """Initialize with the given values."""
        self.input_path = input_path
        self.write = write


def interpret_args(args: argparse.Namespace) -> Args:
    """Parse the command-line arguments."""
    input_path = pathlib.Path(args.input)
    write = bool(args.write)

    return Args(input_path=input_path, write=write)


# fmt: off
@ensure(
    lambda lines, result:
    result[1] is not None or len(lines) == len(result[0])
)
@ensure(
    lambda result:
    (result[0] is None) ^ (result[1] is None),
    "Either sealed lines or error, but not both and not none of the two"
)
# fmt: on
def seal(
    lines: thonnycontrib.thonny_sealed.Lines,
) -> Tuple[Optional[thonnycontrib.thonny_sealed.Lines], Optional[str]]:
    """
    Seal the text based on its sealing comments.

    Return (sealed text, error if any).
    """
    markers = thonnycontrib.thonny_sealed.extract_markers(lines)
    blocks, error = thonnycontrib.thonny_sealed.parse_blocks(markers=markers)

    if error:
        return None, error

    assert blocks is not None

    result = []  # type: List[str]

    if len(blocks) == 0:
        return lines, None

    result.extend(lines[: blocks[0].first.lineno])
    for i, block in enumerate(blocks):
        if i > 0:
            result.extend(lines[blocks[i - 1].last.lineno + 1 : block.first.lineno])

        # We need to insert the current block index so that copy/pasting a block
        # multiple times does not produce undesired sealed blocks.
        content = "\n".join(lines[block.first.lineno + 1 : block.last.lineno])
        content_to_seal = f"{i}.{content}"
        md5hex = hashlib.md5(content_to_seal.encode("utf-8")).hexdigest()

        # Just append the last 8 characters. The collisions are possible, but very
        # unlikely.
        truncated_md5 = md5hex[-8:]

        result.append(f"{block.first.prefix.rstrip()} {truncated_md5}")
        result.extend(lines[block.first.lineno + 1 : block.last.lineno])
        result.append(f"{block.last.prefix.rstrip()} {truncated_md5}")

    result.extend(lines[blocks[-1].last.lineno + 1 :])

    return thonnycontrib.thonny_sealed.assert_lines(lines=result), None


def run(args: Args, stdout: TextIO, stderr: TextIO) -> int:
    """Run the program on the input."""
    if not args.input_path.exists():
        stderr.write(f"The input does not exist: {args.input_path}\n")
        return 1

    if not args.input_path.is_file():
        stderr.write(f"The input is not a file: {args.input_path}\n")
        return 1

    content = args.input_path.read_text(encoding="utf-8")
    lines = thonnycontrib.thonny_sealed.assert_lines(content.splitlines())
    sealed_lines, error = seal(lines=lines)
    if error:
        stderr.write(
            f"There was an error while sealing the file {args.input_path}:\n"
            f"{error}\n"
        )
        return 1

    assert sealed_lines is not None

    sealed_content = "\n".join(sealed_lines)
    if content.endswith("\n"):
        sealed_content += "\n"

    if error:
        stderr.write(f"{error}\n")
        return 1

    assert sealed_lines is not None

    if args.write:
        tmp_pth = args.input_path.parent / (f"{args.input_path.name}.{uuid.uuid4()}")
        try:
            tmp_pth.write_text(sealed_content, encoding="utf-8")
            shutil.move(str(tmp_pth), str(args.input_path))
        finally:
            if tmp_pth.exists():
                tmp_pth.unlink()
    else:
        stdout.write(sealed_content)
        if not sealed_content.endswith("\n"):
            stdout.write("\n")

    return 0


def entry_point() -> int:
    """Execute the main routine."""
    parser = set_up_parser()
    args = interpret_args(args=parser.parse_args())

    return run(args=args, stdout=sys.stdout, stderr=sys.stderr)
