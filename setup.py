from setuptools import setup
from setuptools.command.test import test as TestCommand
import os
import sys

# Find __version__ without import that requires dependencies to be installed:
exec(open(os.path.join(
    os.path.dirname(__file__), 'hangups/version.py'
)).read())


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True
    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


with open('README.rst') as f:
    readme = f.read()


setup(
    name='hangups',
    version=__version__,
    description=('the first third-party instant messaging client for Google '
                 'Hangouts'),
    long_description=readme,
    url='https://github.com/tdryer/hangups',
    author='Tom Dryer',
    author_email='tomdryer.com@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    packages=['hangups', 'hangups.ui'],
    install_requires=[
        'ConfigArgParse==0.9.3',
        'aiohttp==0.9.1',
        'appdirs==1.3.0',
        'purplex==0.2.4',
        'requests==2.3.0',
        'robobrowser==0.5.1',
        # use forked urwid to allow easy installation of version with asyncio
        'hangups-urwid==1.2.2-dev',
        # Backports for py3.3:
        'enum34==1.0',
        'asyncio==3.4.1',
    ],
    tests_require=[
        'pytest',
    ],
    cmdclass={'test': PyTest},
    entry_points={
        'console_scripts': [
            'hangups=hangups.ui.__main__:main',
        ],
    },
)
