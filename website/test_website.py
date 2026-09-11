"""Public output contracts: routes, assets, translations, and invitation state."""
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlsplit, unquote

from build import ROOT, LANGUAGES, SCREENS, build, load_content


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
                ids = {attrs["id"] for _, attrs in elements if "id" in attrs}
                for tag, attrs in elements:
                    self.assertNotIn(tag, ("script", "iframe", "form"))
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
                    for attribute in ("href", "src"):
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
        expected = {"index.html", ".nojekyll", "assets/style.css", "assets/app-icon.png"}
        expected |= {f"{lang}/index.html" for lang in LANGUAGES}
        expected |= {f"assets/screenshots/{lang}-{screen}.png" for lang in LANGUAGES for screen in SCREENS}
        actual = {str(path.relative_to(self.output)) for path in self.output.rglob("*") if path.is_file()}
        self.assertEqual(actual, expected)

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
