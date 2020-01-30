=====
Users
=====

This section describe how to use this project, available tools and
how to use them.

All tools are available under the ``tools`` directory.

Please first refer on how to setup `configuration`_ for oslo.tools.

List oslo projects
==================

Allow you to list oslo projects defined in governance.

For the following example consider you store your git repositories
under the ``~/dev`` directory, where you have already cloned the `governance`_
project.

Usage::

    $ tools/list_oslo_projects.py
    $ tools/list_oslo_projects.py --repo_root ~/dev/

Or by using tox::

    $ tox -e list-oslo-projects -- --repo_root ~/dev/

.. _configuration: ../configuration/index.html
.. _governance: https://opendev.org/openstack/governance/
