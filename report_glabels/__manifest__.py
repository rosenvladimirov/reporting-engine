# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Glabels Reports',
    'version': '11.0.0.1',
    'category': 'Reporting',
    'summary': 'Reports by glabels-engine',
    'description': """
        Extention of report using Glabels (http://glabels.org/).
        GLabels is a GNU/Linux program for creating labels and business cards.
        It is designed to work with various laser/ink-jet peel-off label
        and business card sheets that you’ll find at most office supply stores.

        Glabels uses a template for the label design and are using a special
        notation, ${name}, for including fields from the database. When you
        design your labels use a dummy csv-file for your model you want
        to tie the report to and the format "Text: coma separated Values
        (CSV) with keys on line 1". When the template is ready you can
        upload it to the report-record (or include it in the xml-record if
        you are building a module). There is a test report action that
        also lists all fields for the choosen model.

        This module needs Glabel to be installed on the server (for Ubuntu:
        sudo apt install glabels)

        Test your template using glabels-batch-command:
        glabels-3-batch -o <out-file> -l -C -i <csv-file> <your template.glabels>

""",
    'author': 'dXFactory Ltd., Vertel AB',
    'website': 'http://www.dxfactory.eu',
    'depends': ['base', 'stock', 'base_report_to_printer'],
    'external_dependencies': {'python': ['unicodecsv',], 'bin': ['glabels-3-batch']},
    'data': [
             "views/report_view.xml",
             "views/webclient_templates.xml",
             "views/stock_picking_views.xml",
             "views/stock_move_view.xml",
             "wizard/report_test.xml",
             ],
    'demo': ['demo/demo_report.xml',],
    "license" : "AGPL-3",
    'installable': True,
    'active': False,
    'application': True,
    'auto_install': False,
}
