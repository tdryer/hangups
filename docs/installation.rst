Installation
============

hangups requires `Python`_ 3.6+ and is known to work on Linux, Mac OS X, and
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

An official `hangups Docker image`_ is available.

.. _hangups Docker image: https://registry.hub.docker.com/r/tdryer/hangups

Use Docker to run hangups in a container::

    docker run -it --rm tdryer/hangups

To remember your login session between runs, specify a bind mount for the
hangups cache directory::

    docker run -it --rm --mount type=bind,source=$HOME/.cache/hangups,target=/home/hangups/.cache/hangups tdryer/hangups

To upgrade hangups, pull the latest version of the image::

  docker pull tdryer/hangups

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

