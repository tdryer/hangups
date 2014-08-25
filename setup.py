from setuptools import setup
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True
    def run_tests(self):
        import pytest
        pytest.main(self.test_args)


with open('README.rst') as f:
    readme = f.read()


setup(
    name='hangups',
    version='0.1.3',
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
    packages=['hangups'],
    install_requires=[
        'purplex==0.2.4',
        'tornado==3.2.1',
        'requests==2.2.1',
        'urwid==1.2.1',
        'appdirs==1.3.0',
    ],
    tests_require=[
        'pytest',
    ],
    cmdclass={'test': PyTest},
    entry_points={
        'console_scripts': [
            'hangups=hangups.__main__:main',
        ],
    },
)
