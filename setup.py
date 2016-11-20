# -*- coding: utf-8 -*-

import sys
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


def read_description():
    with open('README.rst') as fd:
        return fd.read()


class PyTest(TestCommand):
    user_options = [
        ('pytest-args=', 'a', "Arguments to pass to py.test"),
    ]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args or ['--cov-report=term-missing'])
        sys.exit(errno)


setup(
    name='paratest',
    version='2.0.0',
    description=(
        "Test paralelizer"
    ),
    long_description=read_description(),
    cmdclass={'test': PyTest},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: '
        'Libraries :: Application Frameworks',
    ],
    keywords='parallel test',
    author='Miguel Ángel García',
    author_email='miguelangel.garcia@gmail.com',
    url='https://github.com/paratestproject/paratest',
    license='MIT',
    packages=find_packages('.'),
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'paratest = paratest.paratest:main',
        ],
    },
    include_package_data=True,
    package_dir={
        'paratest/plugins': 'plugins',
    },
    package_data={
        'paratest/plugins': ['plugins/*.paratest', 'plugins/plugin_hook'],
    },
    install_requires=[
    ],
    tests_require=[
        'pexpect',
        'pytest',
        'pytest-cov',
        'paratest-dummy',
    ],
)
