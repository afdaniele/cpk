Use remote machines
===================

The term **machine** in cpk is used to indicate an endpoint, that is
reachable over the internet and on which we want to build and run
our projects.

It is convenient to let `cpk` handle our machines, so that we don't have
to insert passwords or type in long and hard to remember hostnames or
IP addresses.

For example, we are working on a new project and we want to be able to
test it on a workstation in our office while we are working from home,
maybe using a not too powerful laptop.
In this case, we would register our workstation as a `cpk` machine and
then tell cpk to build and run our project there instead of our laptop.

Machines are managed using the command ``cpk machine``.


Create a Machine
----------------

Using the example above, we assume that our workstation is reachable
at the IP address `10.0.0.1`. We have two ways of connecting to our
workstation, TCP or SSH.


Create an SSH Machine (recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We assume that our workstation is configured to accept SSH connections
and that we have an account with username `myuser` on our workstation.

We create a `cpk` machine called `myws` using the command,

.. code-block:: bash

    $ cpk machine create myws myuser@10.0.0.1

Connections based on SSH are made using 2048 bit RSA keypairs that `cpk`
creates and exchanges with the destination machine. For `cpk` to install
the key on the destination, we will be prompted to insert the user password.

.. note::
    The SSH password is only needed to transfer the keys, it is not stored
    and/or used by cpk for anything else.

Once the keys are transferred, we are ready to use the new machine.


Create a TCP Machine (unsecure, not recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::
    TCP connections are not encrypted and require that the destination
    exposes the Docker endpoint to the network. This is very dangerous and
    only suggested within a private local network.

We create a `cpk` machine called `myws` using the command,

.. code-block:: bash

    $ cpk machine create myws 10.0.0.1


List Machines
-------------

We can list the machines stored by `cpk` by running the command,

.. code-block:: bash

    $ cpk machine list

A shortcut for the command above is ``cpk machine ls``.

Remove a Machine
----------------

We can remove a machine called ``myws`` using the command,

.. code-block:: bash

    $ cpk machine remove myws

A shortcut for the command above is ``cpk machine rm``.
