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

Plugins should implement the next interface:

- ``find(path, pattern)``: returns a list of test unique names ("TID", or "Test ID"), searching from ``path`` and filtering by ``pattern``.
- ``run(id, tid, workspace, output_path)``: receives the worker ``id``, one ``tid`` returned by ``find`` in order to execute it, the ``workspace`` path to take input files and the ``output`` path to leave results.


.. _`Jenkins`: https://jenkins.io
.. _`TeamCity`: https://www.jetbrains.com/teamcity/
.. _`Go-CD`: https://www.go.cd/
.. _`Bamboo`: https://es.atlassian.com/software/bamboo/
