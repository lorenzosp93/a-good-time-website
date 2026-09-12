"""Public output contracts: routes, assets, translations, and invitation state."""
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlsplit, unquote, parse_qs
from support import load_support, export_issue_forms, email_body, EMAIL, REPOSITORY

from build import ROOT, LANGUAGES, SCREENS, motion_screens, build, load_content


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class WebsiteTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name)
        self.config = json.loads((ROOT / "config.json").read_text())

    def check_output(self, base, enabled):
        build(self.output, config=self.config, base_path=base)
        for route, language in [("", "en")] + [(lang, lang) for lang in LANGUAGES]:
            with self.subTest(route=route, enabled=enabled):
                text = (self.output / route / "index.html").read_text()
                page = Page(text)
                elements = page.elements
                self.assertEqual(next(attrs["lang"] for tag, attrs in elements if tag == "html"), language)
                self.assertEqual(sum(tag == "h1" for tag, _ in elements), 1)
                self.assertEqual(sum(tag == "details" for tag, _ in elements), 5)
                self.assertTrue(any(tag == "meta" and attrs.get("name") == "description" and attrs.get("content") for tag, attrs in elements))
                self.assertEqual(sum(tag == "link" and attrs.get("rel") == "alternate" for tag, attrs in elements), 4)
                self.assertTrue(any(tag == "a" and attrs.get("href") == "https://lorenzosp.com" for tag, attrs in elements))
                self.assertEqual(sum(tag == "video" for tag, _ in elements), len(motion_screens(language)))
                self.assertTrue(all("loop" not in attrs and "autoplay" not in attrs for tag, attrs in elements if tag == "video"))
                self.assertFalse(any(tag == "details" and "open" in attrs for tag, attrs in elements))
                ids = {attrs["id"] for _, attrs in elements if "id" in attrs}
                for tag, attrs in elements:
                    self.assertNotIn(tag, ("iframe", "form"))
                    if tag == "img":
                        self.assertIn("alt", attrs)
                        self.assertIn("width", attrs)
                        self.assertIn("height", attrs)
                    if attrs.get("class") == "cta":
                        self.assertEqual(tag, "a" if enabled else "button")
                        if enabled:
                            self.assertEqual(attrs["href"], self.config["testflight_url"])
                        else:
                            self.assertIn("disabled", attrs)
                            self.assertNotIn("href", attrs)
                    for attribute in ("href", "src", "poster", "data-src"):
                        if attribute not in attrs:
                            continue
                        url = urlsplit(attrs[attribute])
                        if url.scheme:
                            self.assertIn(tag, ("link", "a"))
                            self.assertEqual(url.scheme, "https")
                        elif not url.path:
                            self.assertIn(url.fragment, ids)
                        else:
                            self.assertTrue(url.path.startswith(base + "/"))
                            target = self.output / unquote(url.path[len(base):]).lstrip("/")
                            if url.path.endswith("/"):
                                target /= "index.html"
                            self.assertTrue(target.is_file(), f"Broken {attribute}: {attrs[attribute]}")
                self.assertEqual(sum(attrs.get("class") == "cta" for _, attrs in elements), 2)
                copy = load_content()[language]
                if enabled:
                    self.assertNotIn(copy["cta_soon"], text)
                    self.assertNotIn(copy["closing_note"], text)
        expected = {"index.html", ".nojekyll", "assets/style.css", "assets/motion.js", "assets/app-icon.png"}
        expected |= {f"{lang}/index.html" for lang in LANGUAGES}
        expected |= {f"assets/screenshots/{lang}-{screen}.png" for lang in LANGUAGES for screen in SCREENS}
        expected |= {f"assets/demos/{lang}-{screen}.mp4" for lang in LANGUAGES for screen in motion_screens(lang)}
        expected |= {"assets/support.js", "support/index.html"} | {f"{lang}/support/index.html" for lang in LANGUAGES}
        actual = {str(path.relative_to(self.output)) for path in self.output.rglob("*") if path.is_file()}
        self.assertEqual(actual, expected)

    def test_support_routes_forms_and_email_fallbacks(self):
        for base in ("", "/a-good-time-website"):
            build(self.output, config=self.config, base_path=base)
            content = load_support()
            for route, lang in [("support", "en")] + [(f"{lang}/support", lang) for lang in LANGUAGES]:
                text = (self.output / route / "index.html").read_text()
                page = Page(text)
                self.assertIn(content[lang]["public_notice"], text)
                self.assertEqual(sum(tag == "h1" for tag, _ in page.elements), 1)
                self.assertFalse(any(tag in ("form", "iframe") for tag, _ in page.elements))
                ids = {a["id"] for _, a in page.elements if "id" in a}
                templates, drafts = set(), []
                for tag, attrs in page.elements:
                    if "data-copy" in attrs:
                        self.assertIn(attrs["data-copy"], ids)
                        self.assertIn("hidden", attrs)  # No broken controls without JS.
                    for attribute in ("href", "src"):
                        if attribute not in attrs:
                            continue
                        url = urlsplit(attrs[attribute])
                        if url.scheme == "mailto":
                            self.assertEqual(url.path, EMAIL)
                            if url.query:
                                drafts.append(parse_qs(url.query)["body"][0])
                        elif url.netloc == "github.com" and url.path.endswith("/issues/new"):
                            self.assertEqual(attrs.get("aria-describedby"), "public-notice")
                            self.assertEqual(set(parse_qs(url.query)), {"template"})
                            templates.add(parse_qs(url.query)["template"][0])
                        elif not url.scheme:
                            if not url.path:
                                self.assertIn(url.fragment, ids)
                            else:
                                self.assertTrue(url.path.startswith(base + "/"))
                                target = self.output / url.path[len(base):].lstrip("/")
                                if url.path.endswith("/"):
                                    target /= "index.html"
                                self.assertTrue(target.is_file(), attrs[attribute])
                self.assertEqual(templates, {f"{cat['id']}-{lang}.yml" for cat in content[lang]["categories"]})
                self.assertEqual(drafts, [email_body(content[lang], cat) for cat in content[lang]["categories"]])
                self.assertIn(EMAIL, text)

    def test_issue_form_export_contract(self):
        destination = self.output / "templates"
        export_issue_forms(destination)
        self.assertEqual(len(list(destination.glob("*.yml"))), 10)
        for lang, values in load_support().items():
            for category in values["categories"]:
                form = json.loads((destination / f"{category['id']}-{lang}.yml").read_text())
                self.assertIn("needs-triage", form["labels"])
                self.assertIn(values["public_notice"], form["body"][0]["attributes"]["value"])
                fields = {field["id"]: field for field in form["body"] if "id" in field}
                self.assertEqual(len(fields), len(form["body"]) - 1)
                self.assertTrue(fields["surface"]["validations"]["required"])
                self.assertFalse(fields["additional"]["validations"]["required"])
                self.assertTrue(fields["public-consent"]["attributes"]["options"][0]["required"])
                self.assertEqual([field["attributes"]["label"] for key, field in fields.items() if key.startswith("answer-")], category["fields"])
        self.assertFalse(json.loads((destination / "config.yml").read_text())["blank_issues_enabled"])
        published = ROOT.parent / ".github/ISSUE_TEMPLATE"
        if published.is_dir():
            for expected in destination.glob("*.yml"):
                actual = published / expected.name
                self.assertTrue(actual.is_file(), f"Missing exported form: {expected.name}")
                self.assertEqual(json.loads(actual.read_text()), json.loads(expected.read_text()), f"Stale exported form: {expected.name}")

    def test_coming_soon_on_github_project_path(self):
        self.config["testflight_url"] = ""
        self.check_output("/a-good-time", False)

    def test_invitation_on_github_project_path(self):
        self.config["testflight_url"] = "https://testflight.apple.com/join/Example1"
        self.check_output("/a-good-time", True)

    def test_local_preview(self):
        self.config["testflight_url"] = ""
        self.check_output("", False)

    def test_public_repository_path(self):
        self.config["testflight_url"] = ""
        self.check_output(urlsplit(self.config["site_url"]).path.rstrip("/"), False)

    def test_unexpected_output_file_is_not_published(self):
        (self.output / "private-notes.txt").write_text("Not public")
        with self.assertRaises(ValueError):
            build(self.output, config=self.config)

    def test_invalid_invitation_rejected(self):
        for invitation in ("#", "javascript:alert(1)", "https://example.com", "http://testflight.apple.com/join/test"):
            with self.subTest(invitation=invitation):
                self.config["testflight_url"] = invitation
                with self.assertRaises(ValueError):
                    build(self.output, config=self.config)


if __name__ == "__main__":
    unittest.main()
