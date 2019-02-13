// © 2017 Creu Blanca
// License AGPL-3.0 or later (https://www.gnuorg/licenses/agpl.html).
odoo.define('report_glabels.report', function(require){
'use strict';

var ActionManager= require('web.ActionManager');
var crash_manager = require('web.crash_manager');
var core = require('web.core');
var framework = require('web.framework');
var rpc = require('web.rpc');

ActionManager.include({
    ir_actions_report: function (action, options){
        var self = this;
        var cloned_action = _.clone(action);
        var _t = core._t;
        var _super = this._super;

        if (cloned_action.report_type === 'glabels') {
            framework.blockUI();
            var report_glabels_url = 'report/glabels/' + cloned_action.report_name;
            if(cloned_action.context.active_ids){
                report_glabels_url += '/' + cloned_action.context.active_ids.join(',');
            }else{
                report_glabels_url += '?options=' + encodeURIComponent(JSON.stringify(cloned_action.data));
                report_glabels_url += '&context=' + encodeURIComponent(JSON.stringify(cloned_action.context));
            }
            console.log("Print action", cloned_action, report_glabels_url);
            rpc.query({
                model: 'ir.actions.report',
                method: 'print_action_for_report_name',
                args: [cloned_action.report_name]
            }).then(function (print_action) {
                if (print_action && print_action.action === 'server') {
                    framework.unblockUI();
                    rpc.query({
                        model: 'ir.actions.report',
                        method: 'print_document_glabels',
                        args: [cloned_action.id, cloned_action.context.active_ids],
                        kwargs: {data: cloned_action.data || {'report_name': cloned_action.report_name}},
                        context: cloned_action.context || {}
                    }).then(function () {
                        self.do_notify(_t('Report'),
                            _.str.sprintf(_t('Document sent to the printer %s'), print_action.printer_name));
                    }).fail(function () {
                        self.do_notify(_t('Report'),
                            _.str.sprintf(_t('Error when sending the document to the printer '), print_action.printer_name));
                    });
                } else {
                    self.getSession().get_file({
                        url:   report_glabels_url,
                        data:  {data: JSON.stringify([
                                    report_glabels_url,
                                    cloned_action.report_type
                                ])},
                        error: crash_manager.rpc_error.bind(crash_manager),
                        success: function (){
                            if(cloned_action && options && !cloned_action.dialog){
                                    options.on_close();
                            }
                        }
                        });
                    framework.unblockUI();
                    return;
                }
            });
        } else {
            return _super.apply(self, [cloned_action, options]);
        }
        }
    });
});
