
PyNEST
======

Python bindings for NEST Simulator.


Installation
------------

It is recommended to install the package into an environment. For example
using Python `venv` could be done as follows:

```bash
python -m venv venv
source venv/bin/activate
pip install -U pip
pip install .
```

Development and Testing
-----------------------

To install in development mode use

```bash
pip install -e .[dev]
```

in the cloned repository instead of the last line in the normal installation
procedure.

To run the test suite type

```bash
pytest nest
```


License
-------

This project is licensed under GNU General Public License v2.0 or later.
See LICENSE for details.

```
SPDX-License-Identifier: GPL-2.0-or-later
SPDX-Copyright: 2004, The NEST Initiative
SPDX-Author: The NEST Initiative <users@nest-simulator.org>
```
