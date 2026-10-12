# Copyright 2026 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
import io
import unittest

from odoo.exceptions import UserError, ValidationError
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode

from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools.misc import file_open

from ..models.ir_report import parse_glabels_columns
from ..glabels_loader import load_glabels

try:
    from odoo.tools.pdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None


GLABELS = load_glabels()


def _pdf_text(page):
    # pypdf връща интервалите от PDF-а на Qt като табулации
    return " ".join(page.extract_text().split())


def _data(name):
    with file_open(f"report_glabels/tests/data/{name}", "rb") as fh:
        return fh.read()


@tagged("post_install", "-at_install")
class TestReportGLabels(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, lang="en_US"))
        cls.country = cls.env.ref("base.bg")
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Примерен партньор",
                "ref": "34111",
                "country_id": cls.country.id,
                "is_company": True,
            }
        )
        # Формата е създадена „от човек“: няма свой модел report.<име>
        cls.report = cls.env["ir.actions.report"].create(
            {
                "name": "Partner test label",
                "model": "res.partner",
                "report_type": "glabels",
                "report_name": "report_glabels.test_form_without_model",
                "glabels_template_file": base64.b64encode(
                    _data("partner_name.glabels")
                ),
                "glabels_template_filename": "partner_name.glabels",
                "glabels_csv_file": base64.b64encode(_data("partner_name.csv")),
                "glabels_csv_filename": "partner_name.csv",
            }
        )
        cls.engine = cls.env["report.report_glabels.abstract"]

    # --- колоните ------------------------------------------------------

    def test_columns_come_from_first_csv_line_only(self):
        csv_bytes = b"\xef\xbb\xbfname, ref ,\nx,y\nz,w\n"
        self.assertEqual(parse_glabels_columns(csv_bytes), ["name", "ref"])
        self.assertEqual(self.report._glabels_get_columns(), ["name", "ref"])
        self.assertEqual(self.report.glabels_columns, "name\nref")

    def test_column_gLabels_cannot_parse_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.report.glabels_csv_file = base64.b64encode(b"name,price:x\n")
        with self.assertRaises(ValidationError):
            self.report.glabels_csv_file = base64.b64encode(b"\n")

    # --- стойностите ---------------------------------------------------

    def test_action_read_with_bin_size_like_the_web_client(self):
        """Уеб клиентът зарежда действието с bin_size=True (/web/action/load).

        МУТАЦИЯ: `self.glabels_csv_file` вместо `with_context(bin_size=False)`
        в `_glabels_get_columns` ⇒ Binary връща „N bytes“ и base64 пада с
        Incorrect padding — точно грешката на Ина от 28.09.2026.
        """
        action = (
            self.env["ir.actions.report"]
            .with_context(bin_size=True)
            .sudo()
            .browse(self.report.id)
        )
        action.invalidate_recordset()
        values = action.read()[0]
        self.assertEqual(values["glabels_columns"], "name\nref")

    def test_field_path_values(self):
        value = self.engine._glabels_value
        self.assertEqual(value(self.partner, "name"), "Примерен партньор")
        self.assertEqual(value(self.partner, "ref"), "34111")
        self.assertEqual(value(self.partner, "country_id"), self.country.display_name)
        self.assertEqual(value(self.partner, "country_id.code"), "BG")
        self.assertEqual(value(self.partner, "is_company"), "1")
        # празна релация по пътя е празен низ, не грешка
        self.assertEqual(value(self.partner, "parent_id.name"), "")

    def test_magic_values(self):
        value = self.engine._glabels_value
        self.assertEqual(value(self.partner, "creator"), self.env.user.name)
        self.assertEqual(value(self.partner, "company"), self.env.company.name)
        self.assertTrue(value(self.partner, "date_now"))

    def test_unknown_column_is_an_error_not_a_blank(self):
        self.assertIsNone(self.engine._glabels_value(self.partner, "no_such_field"))
        # път през поле, което не е релация
        self.assertIsNone(self.engine._glabels_value(self.partner, "name.x"))
        with self.assertRaisesRegex(UserError, "no_such_field"):
            self.engine._glabels_rows(self.partner, ["name", "no_such_field"])

    def test_rows_keep_csv_column_order(self):
        rows = self.engine._glabels_rows(self.partner, ["ref", "name"])
        self.assertEqual(rows, [{"ref": "34111", "name": "Примерен партньор"}])

    # --- прегледът в gLabels ---------------------------------------------

    def test_preview_values_are_the_printed_values(self):
        """Прегледът дава същото като редовете за печат, по колоните на CSV-то."""
        preview = self.report.glabels_preview_values(self.partner.ids)
        printed = self.engine.with_context(
            glabels_report_id=self.report.id
        )._glabels_rows(self.partner, ["name", "ref"])
        self.assertEqual(preview["unknown"], [])
        self.assertEqual(preview["rows"], [dict(printed[0], id=self.partner.id)])

    def test_preview_unknown_column_is_reported_not_raised(self):
        """Етикетът се проектира: непозната колона е празна клетка + `unknown`."""
        preview = self.report.glabels_preview_values(
            self.partner.ids, ["ref", "no_such_field", "country_id.code"]
        )
        self.assertEqual(preview["unknown"], ["no_such_field"])
        self.assertEqual(
            preview["rows"],
            [{"id": self.partner.id, "ref": "34111", "no_such_field": "",
              "country_id.code": "BG"}],
        )

    def test_preview_skips_missing_records(self):
        gone = self.env["res.partner"].create({"name": "x"})
        gone_id = gone.id
        gone.unlink()
        preview = self.report.glabels_preview_values([gone_id, self.partner.id])
        self.assertEqual([row["id"] for row in preview["rows"]], [self.partner.id])

    def test_preview_only_for_glabels_reports(self):
        other = self.env["ir.actions.report"].search(
            [("report_type", "=", "qweb-pdf")], limit=1
        )
        with self.assertRaisesRegex(UserError, "not a gLabels report"):
            other.glabels_preview_values(self.partner.ids)

    def test_form_without_own_model_uses_engine(self):
        self.assertIsNone(self.env.get("report.report_glabels.test_form_without_model"))
        if GLABELS is None:
            with self.assertRaisesRegex(UserError, "not installed"):
                self.env["ir.actions.report"]._render_glabels(
                    self.report.report_name, self.partner.ids, {}
                )

    # --- рендерирането (само където библиотеката е инсталирана) --------

    @unittest.skipIf(GLABELS is None, "gLabels not installed")
    def test_render_fills_the_merge_fields(self):
        pdf, report_type = self.env["ir.actions.report"]._render_glabels(
            self.report.report_name, self.partner.ids, {}
        )
        self.assertEqual(report_type, "glabels")
        self.assertTrue(pdf.startswith(b"%PDF"))
        if PdfReader is None:
            return
        reader = PdfReader(io.BytesIO(pdf))
        self.assertEqual(len(reader.pages), 1)
        text = _pdf_text(reader.pages[0])
        # 🚨 Празни `${полета}` рендерират „успешно“ — затова се мери ТЕКСТЪТ
        self.assertIn("Примерен партньор", text)
        self.assertIn("34111", text)

    @unittest.skipIf(GLABELS is None, "gLabels not installed")
    def test_render_one_label_per_record_and_copy(self):
        other = self.partner.copy({"name": "Втори партньор", "ref": "777"})
        self.report.glabels_copies = 2
        pdf, _type = self.env["ir.actions.report"]._render_glabels(
            self.report.report_name, (self.partner | other).ids, {}
        )
        if PdfReader is None:
            return
        reader = PdfReader(io.BytesIO(pdf))
        self.assertEqual(len(reader.pages), 4)
        text = " ".join(_pdf_text(page) for page in reader.pages)
        self.assertEqual(text.count("Втори партньор"), 2)

    @unittest.skipIf(GLABELS is None, "gLabels not installed")
    def test_render_with_bin_size_context(self):
        """МУТАЦИЯ: шаблонът прочетен без `bin_size=False` ⇒ Incorrect padding."""
        self.report.invalidate_recordset()
        pdf, _type = (
            self.env["ir.actions.report"]
            .with_context(bin_size=True)
            ._render_glabels(self.report.report_name, self.partner.ids, {})
        )
        self.assertTrue(pdf.startswith(b"%PDF"))

    @unittest.skipIf(GLABELS is None, "gLabels not installed")
    def test_render_unknown_column_raises(self):
        self.report.glabels_csv_file = base64.b64encode(b"name,no_such_field\n")
        with self.assertRaisesRegex(UserError, "no_such_field"):
            self.env["ir.actions.report"]._render_glabels(
                self.report.report_name, self.partner.ids, {}
            )


@tagged("post_install", "-at_install")
class TestReportGLabelsHttp(HttpCase):
    """Пътят, по който кликва човек: зареждане на действието и изтегляне.

    Тестовете по-горе викат двигателя направо и затова НЕ хванаха грешката
    при бутона Print — тя е в `/web/action/load`, преди двигателя.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Примерен партньор", "ref": "34111"}
        )
        cls.report = cls.env["ir.actions.report"].create(
            {
                "name": "Partner test label",
                "model": "res.partner",
                "report_type": "glabels",
                "report_name": "report_glabels.test_http_label",
                "glabels_template_file": base64.b64encode(
                    _data("partner_name.glabels")
                ),
                "glabels_csv_file": base64.b64encode(_data("partner_name.csv")),
            }
        )

    def test_preview_over_json2(self):
        """По пътя на gLabels: JSON-2 с API ключ, методът е публичен.

        МУТАЦИЯ: преименувай метода на `_glabels_preview_values` — частният
        метод не се вика по RPC и тестът пада.
        """
        admin = self.env.ref("base.user_admin")
        key = self.env["res.users.apikeys"].with_user(admin)._generate(
            scope="rpc", name="glabels test",
            expiration_date=datetime.now() + timedelta(days=1),
        )
        response = self.url_open(
            "/json/2/ir.actions.report/glabels_preview_values",
            data=json.dumps({"ids": self.report.ids, "res_ids": self.partner.ids}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"bearer {key}",
                "X-Odoo-Database": self.env.cr.dbname,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {"rows": [{"id": self.partner.id, "name": "Примерен партньор",
                       "ref": "34111"}],
             "unknown": []},
        )

    def test_web_action_load(self):
        self.authenticate("admin", "admin")
        action = self.make_jsonrpc_request(
            "/web/action/load",
            {"action_id": self.report.id, "context": {"bin_size": True}},
        )
        # /web/action/load чете ВСИЧКИ полета (и изчислява glabels_columns),
        # а връща само позволените — грешката беше при четенето
        self.assertEqual(action["report_type"], "glabels")
        self.assertEqual(action["report_name"], self.report.report_name)

    @unittest.skipIf(GLABELS is None, "gLabels not installed")
    def test_report_download(self):
        self.authenticate("admin", "admin")
        url = f"/report/glabels/{self.report.report_name}/{self.partner.id}"
        # GET: така го вика и изтеглянето в браузъра, без CSRF токен
        response = self.url_open(
            "/report/download?"
            + urlencode(
                {
                    "data": json.dumps([url, "glabels"]),
                    "context": json.dumps({"bin_size": True}),
                }
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"), response.content[:300])
