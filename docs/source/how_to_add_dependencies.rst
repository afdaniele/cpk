Add dependencies to a project
=============================

Dependencies are libraries and tools our application relies on at
build or run-time. They are usually installed via package managers,
like **Aptitude** (``apt`` or ``apt-get``), the **Python Package Index**'s
``pip``, etc.
`cpk` supports both ``apt`` and ``pip3`` package managers.


Add ``apt`` dependency
----------------------

We can list our dependency packages installable through the ``apt``
package manager in the file ``dependencies-apt.txt`` available at
the root of our `cpk` project.

`cpk` allows us to add comments and blank lines in this file, this is
useful when we want to group dependencies together and keep track of
what each dependency is needed for.
For example, a valid ``apt`` dependencies file is the following,

.. code-block::

    # generic tools (this is a comment)
    git

    # dependencies for feature A
    libA
    libB

    # dependencies for feature B
    libC



Add ``pip`` dependency
----------------------

We can list our dependency packages installable through the ``pip3``
package manager in the file ``dependencies-py3.txt`` available at
the root of our `cpk` project.

Similar to what we can do in ``dependencies-apt.txt``, `cpk` allows us
to add comments and blank lines in this file.

A valid ``pip3`` dependencies file is the following,

.. code-block::

    # generic tools (this is a comment)
    numpy
    scipy

    # dependencies for feature A
    flask
