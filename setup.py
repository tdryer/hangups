from setuptools import setup
import os
import sys


# TODO: Switch to ReadTheDocs YAML config to get a newer Python
if sys.version_info < (3, 5, 3) and not os.getenv('READTHEDOCS'):
    # This is the minimum version which has support for `async def`/`await`/
    # `async with` syntax.
    raise RuntimeError("hangups requires Python 3.5.3+")


# Find __version__ without import that requires dependencies to be installed:
exec(open(os.path.join(
    os.path.dirname(__file__), 'hangups/version.py'
)).read())


with open('README.rst') as f:
    readme = f.read()


# Dependencies should be specified as a specific version or version range that
# is unlikely to break compatibility in the future. This is required to prevent
# hangups from breaking when new versions of dependencies are released,
# especially for end-users (non-developers) who use pip to install hangups.
install_requires = [
    'ConfigArgParse==0.11.0',
    'aiohttp>=3.3,<4',
    'async-timeout>=2,<4',
    'appdirs>=1.4,<1.5',
    'readlike==0.1.2',
    'requests>=2.6.0,<3',  # uses semantic versioning (after 2.6)
    'ReParser==1.4.3',
    'protobuf>=3.1.0,<3.12',
    'urwid==1.3.1',
    'MechanicalSoup==0.6.0',
]


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
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Communications :: Chat',
        'Environment :: Console :: Curses',
    ],
    packages=['hangups', 'hangups.ui'],
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'hangups=hangups.ui.__main__:main',
        ],
    },
)
