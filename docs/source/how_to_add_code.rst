Add code to a project
=====================

Code in `cpk` project is organized in packages. `cpk` supports:

    - `Catkin Packages <http://wiki.ros.org/ROS/Tutorials/catkin/CreatingPackage>`_;
    - `Python 3 (Module) Packages <https://docs.python.org/3/tutorial/modules.html#packages>`_;

Both `Catkin` and `Python` packages are basically directories with
a specific structure. Place your `Catkin` and `Python` packages inside
the ``packages/`` directory in your `cpk` project.
This is enough for `cpk` to detect them and configure them for use
inside the Docker container.

Let's see how to add packages to our project.


Launchers
---------

Before we can dive into how to add code to a `cpk` project, let's talk
about the concept of **launchers**. A `launcher` is an executable file
that you can pick as the entrypoint when your project runs. In other words,
the launcher will be the first process that gets executed in the container
when we do ``cpk run``.

A `cpk` project can have multiple launchers, and they are stored in the
``launchers/`` directory at the root of our `cpk` project.
There is always a `default` launcher inside that directory.
The default launcher is a bash script that prints out the string
`"This is an empty launch script. Update it to launch your application."`
and exits.
And that is exactly what you see when you execute the command ``cpk run``
from inside a newly created project.

Any executable file, or script file beginning with a
`shebang <https://en.wikipedia.org/wiki/Shebang_(Unix)>`_, is detected
by `cpk` as a valid launcher.

Changing the content of the default launcher is usually enough for simple
applications, but more complex projects might need multiple launchers,
you can create as many as you need inside the launchers directory.

An example of multi-launcher project could be one in which the default
launcher runs an application in "Release" mode while a secondary ``debug``
launcher launches it in "Debug" mode.

Use the argument ``-L/--launcher`` of ``cpk run`` to run a non-default
launcher.


Create a Python Package
-----------------------

From the root of a `cpk` project, let's move to the packages directory
and create a Python package inside called ``my_python_package`` that is
compliant with the schema of a Python package. If you are not familiar
with the Python package schema, you can learn more by reading the
`official documentation <https://docs.python.org/3/tutorial/modules.html#packages>`_.

.. code-block:: bash

    $ cd ./packages/
    $ mkdir ./my_python_package
    $ cd ./my_python_package
    $ touch __init__.py

The snippet above creates the simplest Python package possible, which
consists of an empty directory called ``my_python_package`` containing
an empty file called ``__init__.py``.

We can now add a Python module to the Python package we just created.
Let's create a very simple module called ``main.py`` inside the directory
``my_python_package/`` with the following content,

.. code-block:: python

    if __name__ == "__main__":
        print("Hello from Python")

The module above implements the classic Python `"Hello world"` example.
Let's build it and run it using `cpk`.
We will begin by telling our default launcher that this is new module
is the application we want to run. We can do so by updating the content
of the file ``launchers/default.sh`` to the following,

.. code-block:: bash

    #!/bin/bash
    python3 -m my_python_package.main

We can now build and run our project using the commands,

.. code-block:: bash

    $ cpk build
    $ cpk run

If everything went well, we should see something like the following,

.. code-block:: bash

    ...
    Hello from Python

This is all we need to know to start packing our `cpk` projects with
custom code.
As you might have noticed, `cpk` took care of discovering our
``my_python_package`` package and adding it to the ``PYTHONPATH``
environment variable.


..
    TODO: Add the section `Add Catkin Package`.