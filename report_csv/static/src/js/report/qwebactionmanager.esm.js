/** @odoo-module **/

import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";

registry
    .category("ir.actions.report handlers")
    .add("csv_handler", async function (action, options, env) {
        if (action.report_type === "csv") {
            const type = action.report_type;
            let url = `/report/${type}/${action.report_name}`;
            const actionContext = action.context || {};

            // Get user context - new Odoo 18 way
            const userService = env.services.user || env.services["user"];
            const userContext = userService ? userService.context : {};

            if (action.data && JSON.stringify(action.data) !== "{}") {
                // Build a query string with `action.data`
                const action_options = encodeURIComponent(JSON.stringify(action.data));
                const context = encodeURIComponent(JSON.stringify(actionContext));
                url += `?options=${action_options}&context=${context}`;
            } else {
                if (actionContext.active_ids) {
                    url += `/${actionContext.active_ids.join(",")}`;
                }
                if (type === "csv") {
                    const context = encodeURIComponent(JSON.stringify(userContext));
                    url += `?context=${context}`;
                }
            }

            env.services.ui.block();
            try {
                await download({
                    url: "/report/download",
                    data: {
                        data: JSON.stringify([url, action.report_type]),
                        context: JSON.stringify(userContext),
                    },
                });
            } finally {
                env.services.ui.unblock();
            }

            const onClose = options.onClose;
            if (action.close_on_report_download) {
                return env.services.action.doAction(
                    { type: "ir.actions.act_window_close" },
                    { onClose }
                );
            } else if (onClose) {
                onClose();
            }
            return Promise.resolve(true);
        }
        return Promise.resolve(false);
    });
