# Copyright (C) 2014-2015  Grupo ESOC <www.grupoesoc.es>
# License AGPL-3.0 or later (https://www.gnuorg/licenses/agpl.html).
{
    "name": "Zipped Reports",
    "version": "17.0.1.0.0",
    "category": "Reporting",
    "website": "https://github.com/OCA/reporting-engine",
    "development_status": "Production/Stable",
    "author": "Rosen Vladimirov, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "application": False,
    "summary": "Allow to zip reports",
    "depends": ["web"],
    "data": [
        "views/ir_actions_report_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "report_zip/static/src/js/report/action_manager_report.esm.js",
        ],
    },
    "external_dependencies": {
        "python": [  # Python third party libraries required for module
            "zipfile"  # Zip file with Python
        ]
    },
}
