Parallelizes test executions.

It is based on plugins in order to support different languages or platforms.

It allows to parallelize the integration/acceptance tests execution in different environments. This way they will took much less time to finish.

ParaTest can be run under any Continuous Integration Server, like Jenkins, TeamCity, Go-CD, Bamboo, etc.

# Current plugins

ParaTest is in an early development stage and it still have no plugins to work. It is just a proof of concept.

# Contribute

## Plugins

Plugins should implement the next interface:

- ``find(path)``: returns a list of test unique names ("TID", or "Test ID"), searching from ``path``.
- ``init_environment(id)``: initializes the environment with unique id ``id``.
- ``run(tid)``: receives one TID returned by ``find`` in order to execute it.
