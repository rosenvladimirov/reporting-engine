/** @odoo-module **/

import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";

function getReportUrl({ report_name, context, data }, env) {
    // Rough copy of action_service.js _getReportUrl method.
    let url = `/report/zip/${report_name}`;
    const actionContext = context || {};

    // Get user context - Odoo 18 compatible way
    const userService = env.services.user || env.services["user"];
    const userContext = userService ? userService.context : {};

    if (data && JSON.stringify(data) !== "{}") {
        const encodedOptions = encodeURIComponent(JSON.stringify(data));
        const encodedContext = encodeURIComponent(JSON.stringify(actionContext));
        return `${url}?options=${encodedOptions}&context=${encodedContext}`;
    }
    if (actionContext.active_ids) {
        url += `/${actionContext.active_ids.join(",")}`;
    }
    const encodedUserContext = encodeURIComponent(JSON.stringify(userContext));
    return `${url}?context=${encodedUserContext}`;
}

async function triggerDownload(action, { onClose }, env) {
    // Rough copy of action_service.js _triggerDownload method.
    env.services.ui.block();

    // Get user context - Odoo 18 compatible way
    const userService = env.services.user || env.services["user"];
    const userContext = userService ? userService.context : {};

    const data = JSON.stringify([getReportUrl(action, env), action.report_type]);
    const context = JSON.stringify(userContext);

    try {
        await download({ url: "/report/download", data: { data, context } });
    } finally {
        env.services.ui.unblock();
    }

    if (action.close_on_report_download) {
        return env.services.action.doAction(
            { type: "ir.actions.act_window_close" },
            { onClose }
        );
    }
    if (onClose) {
        onClose();
    }
}

registry
    .category("ir.actions.report handlers")
    .add("zip_handler", async function (action, options, env) {
        if (action.report_type === "zip") {
            await triggerDownload(action, options, env);
            return true;
        }
        return false;
    });
