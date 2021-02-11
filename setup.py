import sys
from distutils.core import setup


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


if sys.version_info < (3, 5):
    msg = 'cpk works with Python 3.5 and later.\nDetected %s.' % str(sys.version)
    sys.exit(msg)

lib_version = get_version(filename='include/cpk/__init__.py')

setup(
    name='cpk',
    packages=[
        'cpk'
    ],
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
    install_requires=['docker', 'requests', 'jsonschema', 'termcolor', 'pyyaml'],
    scripts=['include/cpk/bin/cpk'],
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
