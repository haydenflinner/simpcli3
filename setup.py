"""simpcli3 module."""

from setuptools import find_packages, setup

with open("README.md") as f:
    readme = f.read()

# Runtime Requirements.
inst_reqs = ["simple_parsing"]

# Dev Requirements
extra_reqs = {
    "test": ["pytest", "pytest-cov"],
    "dev": ["pytest", "pytest-cov", "pre-commit"],
}


setup(
    name="simpcli3",
    version="0.0.2",
    description=u"A Python3 library for turning functions into cmd-line programs trivially.",
    long_description=readme,
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
    classifiers=[
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="cmd line command console argparse argparsing dataclass",
    author=u"Hayden Flinner",
    author_email="haydenflinner@gmail.com",
    url="https://github.com/haydenflinner/simpcli3",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=inst_reqs,
    extras_require=extra_reqs,
    entry_points={"console_scripts": ["simpcli3 = simpcli3.scripts.cli:simpcli3"]},
)
