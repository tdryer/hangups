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

install_requires=[
    'ConfigArgParse==0.9.3',
    'aiohttp==0.15.1',
    'appdirs==1.4.0',
    'purplex==0.2.4',
    'readlike>=0.1',
    'requests==2.6.0',
    'ReParser>=1.4',
    # use forked urwid until there's a 1.3 release with colour bugfix
    'hangups-urwid==1.2.2-dev',
]
if sys.version_info < (3, 4):
    install_requires.append('enum34=1.0.4')
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
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    packages=['hangups', 'hangups.ui'],
    install_requires=install_requires,
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
