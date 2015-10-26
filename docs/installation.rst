Installation
============

hangups requires `Python`_ 3.3 or 3.4, and is known to work on Linux and Mac OS
X.

.. _Python: https://www.python.org/

Python Package Index (PyPI)
---------------------------

hangups is listed in `PyPI`_, and may be installed using `pip`_.

.. _PyPI: https://pypi.python.org/pypi
.. _pip: https://pip.pypa.io/

Simply run pip to install the hangups package::

  pip3 install hangups

Docker
------

hangups is available as an automated build on the Docker Hub as
`tdryer/hangups`_.

.. _tdryer/hangups: https://registry.hub.docker.com/u/tdryer/hangups/

Create a data-only container for hangups to allow upgrading without losing your
login session::

  docker run --name hangups-session --entrypoint true tdryer/hangups

Whenever you want to start hangups, run a new container::

  docker run -it --rm --name hangups --volumes-from hangups-session tdryer/hangups

To upgrade hangups, pull the latest version of the image::

  docker pull tdryer/hangups

Arch Linux
----------

An `unofficial hangups package`_ is available for Arch Linux in the Arch User
Repository.

.. _unofficial hangups package: https://aur.archlinux.org/packages/hangups-git

Install from Source
-------------------

The hangups code is also available from GitHub.

Either download and extract a `hangups release archive`_, or clone the `hangups
repository on GitHub`_::

  git clone https://github.com/tdryer/hangups.git

Switch to the hangups directory and install the package::

  cd hangups
  python3 setup.py install

.. _hangups release archive: https://github.com/tdryer/hangups/releases
.. _hangups repository on GitHub: https://github.com/tdryer/hangups

