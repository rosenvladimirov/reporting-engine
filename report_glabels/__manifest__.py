# Copyright 2025 Rosen
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Base report gLabels",
    "summary": "Base module to create label reports using gLabels templates",
    "author": "Rosen, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/reporting-engine",
    "category": "Reporting",
    "version": "19.0.2.1.1",
    "development_status": "Alpha",
    "license": "AGPL-3",
    # 🔑 `glabels` НЕ е в external_dependencies: иначе модулът не се
    # инсталира там, където библиотеката липсва, и формите не могат да се
    # въведат предварително. Липсата се казва при печат (ADR report-glabels/0001).
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