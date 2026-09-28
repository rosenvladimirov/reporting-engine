# Copyright 2026 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
"""Внасянето на библиотеката glabels — чак при печат (ADR report-glabels/0002).

🚨 Библиотеката е C++/Qt. Счупена инсталация не хвърля ImportError, а спира
ЦЕЛИЯ процес (`qFatal`, например когато не намери шаблоните си). Внесена при
зареждане на модула, тя би свалила Odoo още при старта; внесена при печат,
сваля най-много един печат.

Два пътя до библиотеката:
  * инсталиран пакет (`pip install`) — обикновен `import glabels`;
  * папка, сглобена за сървъра (odoo.sh), със `python/`, `lib/`, `plugins/`,
    `templates/`, `fonts/` и `fonts.conf` — пътят ѝ идва от системния параметър
    `report_glabels.library_path` или от GLABELS_LIBRARY_PATH.
"""

import logging
import os
import sys

_logger = logging.getLogger(__name__)

_glabels = None


def load_glabels(library_path=None):
    """Модулът glabels или None, ако го няма."""
    global _glabels
    if _glabels is not None:
        return _glabels

    # Сървърът няма екран, а Qt тръгва като графично приложение: без
    # offscreen `import glabels` пада, а съобщението не казва „няма дисплей“
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    library_path = library_path or os.environ.get("GLABELS_LIBRARY_PATH")
    if library_path:
        python_dir = os.path.join(library_path, "python")
        plugins_dir = os.path.join(library_path, "plugins")
        if os.path.isdir(python_dir) and python_dir not in sys.path:
            sys.path.insert(0, python_dir)
        if os.path.isdir(plugins_dir):
            # плъгинът offscreen е в сглобената папка, не в системата
            os.environ["QT_PLUGIN_PATH"] = plugins_dir
        fonts_conf = os.path.join(library_path, "fonts.conf")
        if os.path.isfile(fonts_conf):
            # 🚨 без шрифт етикетът излиза без нито една буква и мълчи.
            # fonts.conf на папката включва системния, затова wkhtmltopdf,
            # който наследява средата, вижда същите шрифтове плюс нашите
            os.environ.setdefault("FONTCONFIG_FILE", fonts_conf)

    try:
        import glabels
    except ImportError as exc:
        _logger.debug("Cannot import glabels: %s", exc)
        return None
    _glabels = glabels
    return glabels
