import unittest

from legal_authority_diff.govinfo import (
    govinfo_pdf_url,
    parse_us_reports_citation,
)


class GovInfoCitationTests(unittest.TestCase):
    def test_parse_canonical_us_reports_citation(self):
        self.assertEqual(parse_us_reports_citation("347 U.S. 483"), (347, 483))

    def test_parse_accepts_optional_reporter_periods(self):
        self.assertEqual(parse_us_reports_citation("576 U S 644"), (576, 644))
        self.assertEqual(parse_us_reports_citation("384 U.S. 436"), (384, 436))

    def test_rejects_non_us_reports_citation(self):
        with self.assertRaises(ValueError):
            parse_us_reports_citation("771 F.3d 456")

    def test_build_official_govinfo_url(self):
        self.assertEqual(
            govinfo_pdf_url("347 U.S. 483"),
            "https://www.govinfo.gov/content/pkg/USREPORTS-347/pdf/USREPORTS-347-483.pdf",
        )


if __name__ == "__main__":
    unittest.main()
