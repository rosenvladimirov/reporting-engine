# Copyright 2025 Rosen
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Base report gLabels",
    "summary": "Base module to create label reports using gLabels templates",
    "author": "Rosen, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/reporting-engine",
    "category": "Reporting",
    "version": "19.0.1.0.0",
    "development_status": "Alpha",
    "license": "AGPL-3",
    "external_dependencies": {"python": ["glabels"]},
    "depends": ["base", "web"],
    "data": [
        "views/ir_actions_report_view.xml",
    ],
    "demo": ["demo/report.xml"],
    "installable": True,
    "assets": {
        "web.assets_backend": [
            "report_glabels/static/src/js/report/action_manager_report.esm.js",
        ],
    },
}