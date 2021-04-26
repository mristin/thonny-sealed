import os

import setuptools

here = os.path.abspath(os.path.dirname(__file__))  # pylint: disable=invalid-name

with open(os.path.join(here, "README.rst"), encoding="utf-8") as fid:
    long_description = fid.read()  # pylint: disable=invalid-name

with open(os.path.join(here, "requirements.txt"), encoding="utf-8") as fid:
    install_requires = [line for line in fid.read().splitlines() if line.strip()]

setuptools.setup(
    name="thonny-sealed",
    version="1.0.0b2",
    author="Marko Ristin",
    author_email="marko@ristin.ch",
    description=(
        "Restrict writing to certain areas in the Thonny editor "
        "based on code comments."
    ),
    long_description=long_description,
    url="https://github.com/mristin/thonny-sealed",
    packages=["thonnycontrib.thonny_sealed", "thonny_seal"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: MacOS X",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: End Users/Desktop",
        "License :: Freeware",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Education",
        "Topic :: Software Development",
    ],
    license="License :: OSI Approved :: MIT License",
    keywords="restrict writing problem solution exercise area",
    install_requires=install_requires,
    python_requires=">=3.7",
    # fmt: off
    extras_require={
        "dev": [
            "black==20.8b1",
            "mypy==0.812",
            "pylint==2.3.1",
            "pydocstyle>=2.1.1,<3",
            "coverage>=4.5.1,<5",
            "docutils>=0.14,<1",
            "icontract>=2.5.0",
            "prettytable>=2.1.0,<3",
            "icontract-hypothesis>=1.1.2,<2",
            "twine"
        ],
    },
    package_data={"thonnycontrib.thonny_sealed": ["py.typed"],
                  "thonny_seal": ["py.typed"]},
    # fmt: on
    data_files=[(".", ["LICENSE", "README.rst", "requirements.txt"])],
    entry_points={
        "console_scripts": ["thonny-seal = thonny_seal.main:entry_point"],
        "hypothesis": ["_ = icontract_hypothesis"],
    },
)
