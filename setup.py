from setuptools import setup, find_packages
from pathlib import Path

requires = [
    "Sphinx >= 3.3",
    "hy >= 0.20",
]

def readme():
    try:
        return Path("README.rst").read_text()
    except IOError:
        return None

setup(
    name='sphinxcontrib-hydomain',
    version='0.1.0',
    url='https://github.com/hylang/sphinxcontrib-hydomain',
    license='BSD',
    author='Allison Casey',
    author_email='alliecasey21@gmail.com',
    description='Sphinx domain for documenting HTTP APIs',
    long_description=readme(),
    zip_safe=False,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.9',
        'Topic :: Documentation',
        'Topic :: Utilities',
    ],
    platforms='any',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
    namespace_packages=['sphinxcontrib'],
)
