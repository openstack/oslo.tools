=============
Configuration
=============

oslo.tools uses oslo.config to define and manage configuration
options to allow maintainers to define personal specific configuration
to uses with the different tools available.

Config
======

You can define your own local configuration by creating the ``~/.oslo.conf``
file at the root of your home directory.

For more further reading about how works oslo.config please take a look to the
`documentation`_.

The ``[oslo]`` section is expected in this config file.

In this section you can declare the following options:

- ``repo_root`` which is where you store locally your git repositories
  and where you should clone the `governance`_ project directory

Example of ``oslo.conf`` content::

    [oslo]
    repo_root=~/dev/governance/

Also you can find a file named ``oslo.conf.sample`` at the root of this
project directory, this is a config sample that you can reuse and adapt to
your needs.

.. _documentation: https://docs.openstack.org/oslo.config/latest/
.. _governance: https://opendev.org/openstack/governance/
