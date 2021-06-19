Introduction
============

**cpk** stands for Code Packaging toolKit and is designed to
standardize the way code in a project is structured and
packaged for maximum portability, readability and maintainability.

`cpk` is the result of years of experience in the context of
cross-user, cross-machine, cross-architecture development and deployment
of software modules. Originally created to standardize and simplify
code development and deployment in `Duckietown <https://duckietown.org>`,
it later became an independent toolkit.


Features
========

`cpk` organizes code in **projects**. A `cpk` project is a directory
containing everything that is needed for the project to be built,
packaged, documented and deployed.

The power of `cpk` comes from the technologies it is built on:

- **Python** (for cross-platform availability);
- **Git** (for code versioning);
- **Catkin** (for source code packaging and dependencies management);
- **Docker** (for code packaging and deployment);
- **QEMU** (for cross-platform code building and deployment);
- **SSH** (for fast and secure communication between build and deployment nodes);
- **rsync** (for reliable code synchronization);

The next two sections will jump straight into how to install `cpk`, then
build and run a simple `cpk` project. Don't miss them.


Installation
============

You can install `cpk` through `pip`.

.. code-block:: bash

    $ pip3 install cpk


Get Started
===========

We will now create, build and run an empty project, we will
then take a step back and examine how to populate the project
with your own code.

Create an empty project
-----------------------

Use the following command to create an empty cpk project.

.. code-block:: bash

    $ cpk create ./my_project

You will be asked to provide information about your new project.
For example,

.. code-block:: bash

    cpk|    INFO : Please, provide information about your new project:
       |
       |	Project Name:           my_project
       |	Project Description:    My best project
       |	Owner Username:         afdaniele
       |	Owner Full Name:        Andrea Daniele


Build the project
-----------------

Now that our empty project is created, let's build it.

.. code-block:: bash

    $ cd ./my_project
    $ cpk build

Let it build and you will see a summary of the build that looks like the
following,

.. code-block:: bash

    ...
    ====================================================================================
    Final image name: afdaniele/my_project:latest-amd64
    Base image size: 120.25 MB
    Final image size: 120.25 MB
    Your image added 1.08 KB to the base image.
    -------------------------
    Layers total: 48
     - Built: 48
     - Cached: 0
    -------------------------
    Image launchers:
     - default
    -------------------------
    Time: 5 seconds
    Documentation: Skipped
    ====================================================================================

This means that the project was built successfully, now let's run it.

Run the project
---------------

.. code-block:: bash

    $ cpk run

You will see the following output,

.. code-block:: bash

    ...
    ==> Entrypoint
    <== Entrypoint
    This is an empty launch script. Update it to launch your application.

This means that our project run correctly.
Congratulations, you just built and run your first cpk project.

The following sections will teach you how to,

- :ref:`Add code to a project`;
- :ref:`Use remote machines`;



..
    - `Add launchers to a project`_;
    - `Add dependencies to a project`_;
    - `Add documentation to a project`_;
