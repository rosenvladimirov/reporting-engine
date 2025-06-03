===================
Zip Report Actions
===================

.. !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !! This module enables creation of ZIP archives    !!
   !! from various Odoo reports                       !!
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

This module adds the ability to generate ZIP archives containing multiple reports in Odoo.
Supports AES encryption of archives and various compression options.

**Table of contents**

.. contents::
   :local:

Configuration
============

To use this module, you need to:

* Install the Python library `pyzipper`:

  .. code-block:: bash

    pip install pyzipper

Usage
=====

To create a ZIP report:

#. Go to Settings > Technical > Reports
#. Create a new report or edit an existing one
#. Select report type "Zipped report"
#. Add the reports you want to include in the ZIP archive

Known issues / Roadmap
=====================

Please report bugs at `GitHub Issues
<https://github.com/OCA/{repo}/issues>`_.

Credits
=======

Authors
~~~~~~~

* Rosen Vladimirov

Contributors
~~~~~~~~~~~

* Rosen Vladimirov

Maintainers
~~~~~~~~~~

This module is maintained by:

.. image:: https://www.odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://www.odoo-community.org

OCA, or the Odoo Community Association, promotes collaborative development of Odoo features and
supports the collaborative development of Odoo features and modules.
```

The README.rst file includes:

- Title and brief module description
- Section for configuration with dependency installation instructions
- Section with usage instructions
- Section for bug reporting
- Credits section including authors and contributors
- Maintenance information by OCA

The file follows the standard OCA format and is written in reStructuredText (rst).
