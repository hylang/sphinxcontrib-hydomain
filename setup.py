from pathlib import Path

from setuptools import find_packages, setup

requires = [
    "Sphinx >= 3.3",
    "hy >= 1.0a3",
]


def readme():
    try:
        return Path("README.rst").read_text()
    except OSError:
        return None


setup(
    name="sphinxcontrib-hydomain",
    version="0.1.0",
    url="https://github.com/hylang/sphinxcontrib-hydomain",
    license="BSD",
    author="Allison Casey",
    author_email="alliecasey21@gmail.com",
    description="Sphinx domain for documenting Hy code bases",
    long_description=readme(),
    zip_safe=False,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Documentation",
        "Topic :: Utilities",
    ],
    platforms="any",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
    namespace_packages=["sphinxcontrib"],
)
