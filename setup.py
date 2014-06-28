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
    version='0.1.1',
    description=('reverse-engineered library and basic client for using '
                 'Google\'s Hangouts chat protocol'),
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
        'Programming Language :: Python :: 3.4',
    ],
    packages=['hangups'],
    install_requires=[
        'purplex==0.1.5',
        'tornado==3.2.1',
        'requests==2.2.1',
        'urwid==1.2.1',
    ],
    tests_require=[
        'pytest==2.5.2',
    ],
    cmdclass={'test': PyTest},
    entry_points={
        'console_scripts': [
            'hangups=hangups.__main__:main',
        ],
    },
)
