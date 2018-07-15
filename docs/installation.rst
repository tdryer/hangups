Installation
============

hangups requires `Python`_ 3.5.3+ and is known to work on Linux, Mac OS X, and
Windows (with `Cygwin`_).

.. _Python: https://www.python.org/
.. _Cygwin: http://cygwin.com/

Python Package Index (PyPI)
---------------------------

hangups is listed in `PyPI`_, and may be installed using `pip`_::

  pip3 install hangups

.. _PyPI: https://pypi.python.org/pypi/hangups
.. _pip: https://pip.pypa.io/

Docker
------

hangups is available as an automated build on `Docker Hub`_ as
`tdryer/hangups`_.

.. _tdryer/hangups: https://registry.hub.docker.com/u/tdryer/hangups/

Create a data-only container for hangups to allow upgrading without losing your
login session::

  docker run --name hangups-session --entrypoint true tdryer/hangups

Whenever you want to start hangups, run a new container::

  docker run -it --rm --name hangups --volumes-from hangups-session tdryer/hangups

To upgrade hangups, pull the latest version of the image::

  docker pull tdryer/hangups

.. _Docker Hub: https://hub.docker.com/

Arch Linux
----------

An `unofficial hangups package`_ is available for Arch Linux in the Arch User
Repository.

.. _unofficial hangups package: https://aur.archlinux.org/packages/hangups-git

Install from Source
-------------------

The hangups code is available from GitHub. Either download and extract a
`hangups release archive`_, or clone the `hangups repository`_::

  git clone https://github.com/tdryer/hangups.git

Switch to the hangups directory and install the package::

  cd hangups
  python3 setup.py install

.. _hangups release archive: https://github.com/tdryer/hangups/releases
.. _hangups repository: https://github.com/tdryer/hangups

