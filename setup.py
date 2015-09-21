from setuptools import setup
from setuptools.command.test import test as TestCommand
import os
import sys

# Find __version__ without import that requires dependencies to be installed:
exec(open(os.path.join(
    os.path.dirname(__file__), 'hangups/version.py'
)).read())


class PytestCommand(TestCommand):

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


class PylintCommand(TestCommand):

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pylint.lint
        # Exits with number of messages.
        pylint.lint.Run(['--reports=n', 'hangups', ])


with open('README.rst') as f:
    readme = f.read()


install_requires = [
    'ConfigArgParse==0.9.3',
    'aiohttp==0.17.3',
    'appdirs==1.4.0',
    'purplex==0.2.4',
    'readlike>=0.1',
    'requests==2.6.0',
    'ReParser==1.4.3',
    # use alpha protobuf for official Python 3 support
    'protobuf==3.0.0a3',
    # use forked urwid until there's a 1.3 release with colour bugfix
    'hangups-urwid==1.2.2-dev',
]


if sys.version_info < (3, 4, 3):
    # For Python earlier than 3.4.3, use a backported asyncio that fixes an
    # issue with an exception being logged on exit.
    install_requires.append('asyncio==3.4.3')


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
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Communications :: Chat',
        'Environment :: Console :: Curses',
    ],
    packages=['hangups', 'hangups.ui'],
    install_requires=install_requires,
    tests_require=[
        # >= 2.7.3 required for Python 3.5 support
        'pytest==2.7.3',
        'pylint==1.4.4',
    ],
    cmdclass={
        'test': PytestCommand,
        'lint': PylintCommand,
    },
    entry_points={
        'console_scripts': [
            'hangups=hangups.ui.__main__:main',
        ],
    },
)
