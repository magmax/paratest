====================  =================================================================================
Tests                 |travis| |coveralls|
--------------------  ---------------------------------------------------------------------------------
Downloads             |pip dm| |pip dw| |pip dd|
--------------------  ---------------------------------------------------------------------------------
About                 |pip license| |pip wheel| |pip pyversions| |pip implem|
--------------------  ---------------------------------------------------------------------------------
Status                |version| |status|
====================  =================================================================================

Parallelizes test executions.

It allows to parallelize the integration/acceptance tests execution in different environments. This way they will took much less time to finish.

And it is based on plugins in order to support different languages or platforms.

ParaTest can be run under any Continuous Integration Server, like Jenkins_, TeamCity_, `Go-CD`_, Bamboo_, etc.

Why Paratest?
=============

Almost all test runners allow you to paralellize the test execution, so... why Paratest?

Well... In some cases test execution cannot be parallelized because of depenencies: database access, legacy code, file creation, etc. Then, you need to create a full workspace whenever you want to test them.

This may be a hard task, and sadly Paratest cannot help there.

But with some scripts to clone an existent workspace, Paratest can divide the tests between any number of workspaces, creating them on demand, and running the tests on them. Resources put the limits.

Another advantage of Paratest is the test order: Paratest remembers the time expent in each test and will reorder them to get the most of your infrastructure.


Usage
=====

First of all, you need two things:

- a source. This means to have a source with instructions to create a workspace
- some scripts to setup/teardown the workspaces. This should translate the source into a workspace.

Then, Paratest will call the setup scripts in order to create the workspaces and will parallelize the test run between them.



Current plugins
===============

ParaTest is in an early development stage and it still have no plugins to work. It is just a proof of concept.

Contribute
==========

Plugins
-------

Writting a plugin is quite easy. You can see the `paratest-dummy`_ as example. Just two steps are required:


Write the plugin methods
________________________

Currently, just one method is required:

``def find(path, test_pattern, file_pattern, output_path)``

It should return a dict or a generator for tuples.


Register the entrypoint
_______________________


The second step is to create a ``pip`` package with the entrypoint ``find`` within the group ``paratest``. This should be done in the ``setup.py`` file. Example:

.. code::

   from setuptools import setup, find_packages

   setup(
     name='whatever',
     version='0.0.1',
     entry_points={
       'paratest': 'find = whatever:find'
     }
   )


.. _`Jenkins`: https://jenkins.io
.. _`TeamCity`: https://www.jetbrains.com/teamcity/
.. _`Go-CD`: https://www.go.cd/
.. _`Bamboo`: https://es.atlassian.com/software/bamboo/
.. _`paratest-dummy`: https://github.com/paratestproject/paratest-dummy

.. |travis| image:: https://img.shields.io/travis/paratestproject/paratest.svg
  :target: `Travis`_
  :alt: Travis results

.. |coveralls| image:: https://img.shields.io/coveralls/paratestproject/paratest.svg
  :target: `Coveralls`_
  :alt: Coveralls results_

.. |pip version| image:: https://img.shields.io/pypi/v/paratest.svg
    :target: https://pypi.python.org/pypi/paratest
    :alt: Latest PyPI version

.. |pip dm| image:: https://img.shields.io/pypi/dm/paratest.svg
    :target: https://pypi.python.org/pypi/paratest
    :alt: Last month downloads from pypi

.. |pip dw| image:: https://img.shields.io/pypi/dw/paratest.svg
    :target: https://pypi.python.org/pypi/paratest
    :alt: Last week downloads from pypi

.. |pip dd| image:: https://img.shields.io/pypi/dd/paratest.svg
    :target: https://pypi.python.org/pypi/paratest
    :alt: Yesterday downloads from pypi

.. |pip license| image:: https://img.shields.io/pypi/l/paratest.svg
    :target: https://pypi.python.org/pypi/paratest
    :alt: License

.. |pip wheel| image:: https://img.shields.io/pypi/wheel/paratest.svg
    :target: https://pypi.python.org/pypi/paratest
    :alt: Wheel

.. |pip pyversions| image::  	https://img.shields.io/pypi/pyversions/paratest.svg
    :target: https://pypi.python.org/pypi/paratest
    :alt: Python versions

.. |pip implem| image::  	https://img.shields.io/pypi/implementation/paratest.svg
    :target: https://pypi.python.org/pypi/paratest
    :alt: Python interpreters

.. |status| image::	https://img.shields.io/pypi/status/paratest.svg
    :target: https://pypi.python.org/pypi/paratest
    :alt: Status

.. |version| image:: https://img.shields.io/pypi/v/paratest.svg
    :target: https://pypi.python.org/pypi/paratest
    :alt: Status



.. _Travis: https://travis-ci.org/paratestproject/paratest
.. _Coveralls: https://coveralls.io/r/paratestproject/paratest

.. _@magmax9: https://twitter.com/magmax9

.. _the Affero license: http://opensource.org/licenses/AGPL-3.0
