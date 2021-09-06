import glob
import os
import sys
from distutils.core import setup
from typing import List


def get_version(filename):
    import ast
    version = None
    with open(filename) as f:
        for line in f:
            if line.startswith('__version__'):
                version = ast.parse(line).body[0].value.s
                break
        else:
            raise ValueError('No version found in %r.' % filename)
    if version is None:
        raise ValueError(filename)
    return version


def _get_all_files(parent: str, child: str) -> List[str]:
    path = os.path.abspath(os.path.join(parent, child))
    hidden = glob.glob(os.path.join(path, ".**"), recursive=True)
    nonhidden = glob.glob(os.path.join(path, "**"), recursive=True)
    items = hidden + nonhidden
    files = filter(os.path.isfile, items)
    files = list(map(lambda p: os.path.relpath(p, parent), files))
    return files


def get_decorator_files() -> List[str]:
    this_file = os.path.abspath(__file__)
    cpk_dir = os.path.join(os.path.dirname(this_file), "include", "cpk")
    return _get_all_files(cpk_dir, "decorator")


def get_skeleton_files() -> List[str]:
    this_file = os.path.abspath(__file__)
    cpk_dir = os.path.join(os.path.dirname(this_file), "include", "cpk")
    return _get_all_files(cpk_dir, "skeleton")


if sys.version_info < (3, 6):
    msg = 'cpk works with Python 3.6 and later.\nDetected %s.' % str(sys.version)
    sys.exit(msg)

lib_version = get_version(filename='include/cpk/__init__.py')

setup(
    name='cpk',
    packages=[
        'cpk',
        'cpk.adapters',
        'cpk.cli',
        'cpk.cli.commands',
        'cpk.cli.commands.machine',
        'cpk.cli.commands.endpoint',
        'cpk.utils'
    ],
    package_dir={
        'cpk': 'include/cpk'
    },
    package_data={
        "cpk": [
            "schemas/*/*.json",
            "cli/commands/x-docker",
            *get_decorator_files(),
            *get_skeleton_files()
        ],
    },
    version=lib_version,
    license='MIT',
    description='Toolkit that standardize the way code in a project is structured and packaged '
                'for maximum portability, readability and maintainability.',
    author='Andrea F. Daniele',
    author_email='afdaniele@ttic.edu',
    url='https://github.com/afdaniele/cpk',
    download_url='https://github.com/afdaniele/cpk/tarball/{}'.format(lib_version),
    zip_safe=False,
    include_package_data=True,
    keywords=['code', 'container', 'containerization', 'package', 'toolkit', 'docker'],
    install_requires=[
        'docker>=4.4.0',
        'requests',
        'jsonschema',
        'termcolor',
        'pyyaml',
        'sshconf',
        'cryptography',
        *(['dataclasses'] if sys.version_info < (3, 7) else [])
    ],
    scripts=[
        'include/cpk/bin/cpk'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
