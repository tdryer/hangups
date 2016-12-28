from setuptools import setup
from setuptools.command.test import test as TestCommand
import os
import sys


if sys.version_info < (3, 4, 2):
    # This is the minimum version supported by aiohttp.
    raise RuntimeError("hangups requires Python 3.4.2+")


# Find __version__ without import that requires dependencies to be installed:
exec(open(os.path.join(
    os.path.dirname(__file__), 'hangups/version.py'
)).read())


class PytestCommand(TestCommand):

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ['hangups']
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
        pylint.lint.Run(['--reports=n', 'hangups'])


class Pep8Command(TestCommand):

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pycodestyle
        style_guide = pycodestyle.StyleGuide(config_file='setup.cfg')
        report = style_guide.check_files(['hangups'])
        if report.total_errors:
            sys.exit(1)


with open('README.rst') as f:
    readme = f.read()


# Dependencies should be specified as a specific version or version range that
# is unlikely to break compatibility in the future. This is required to prevent
# hangups from breaking when new versions of dependencies are released,
# especially for end-users (non-developers) who use pip to install hangups.
install_requires = [
    'ConfigArgParse==0.11.0',
    'aiohttp>=1.2,<1.3',
    'appdirs==1.4.0',
    'readlike==0.1.2',
    'requests>=2.6.0,<3',  # uses semantic versioning (after 2.6)
    'ReParser==1.4.3',
    'protobuf>=3.1.0,<3.2.0',
    'urwid==1.3.1',
    'MechanicalSoup==0.6.0',
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
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Communications :: Chat',
        'Environment :: Console :: Curses',
    ],
    packages=['hangups', 'hangups.ui'],
    install_requires=install_requires,
    tests_require=[
        'pytest==3.0.5',
        'pylint==1.6.4',
        'pycodestyle==2.2.0',
        'httpretty==0.8.14',
    ],
    cmdclass={
        'test': PytestCommand,
        'lint': PylintCommand,
        'style': Pep8Command,
    },
    entry_points={
        'console_scripts': [
            'hangups=hangups.ui.__main__:main',
        ],
    },
)
