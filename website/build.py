#!/usr/bin/env python3
"""Build the public website using only Python's standard library."""
import argparse
from html import escape
import json
from pathlib import Path
import re
import shutil
from string import Template
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
LANGUAGES = {"en": "English", "it": "Italiano", "es": "Español"}
SCREENS = ("now", "capture", "focus", "controls")
MOTION_SCREENS = ("focus",)

def motion_screens(lang):
    return ("capture", "focus")



def shape(value):
    if isinstance(value, dict):
        return {key: shape(item) for key, item in value.items()}
    if isinstance(value, list):
        return [shape(item) for item in value]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("All translated values must be nonempty strings")
    return "text"


def load_content():
    content = {lang: json.loads((ROOT / "content" / f"{lang}.json").read_text()) for lang in LANGUAGES}
    expected = shape(content["en"])
    for lang, values in content.items():
        if shape(values) != expected:
            raise ValueError(f"Incomplete translation structure: {lang}")
        if [story["screen"] for story in values["stories"]] != list(SCREENS[1:]):
            raise ValueError(f"Unexpected screenshot order: {lang}")
    return content


def validate_config(config):
    site = urlsplit(config["site_url"])
    if site.scheme != "https" or not site.netloc or site.query or site.fragment:
        raise ValueError("site_url must be an absolute HTTPS URL without query or fragment")
    invitation = config["testflight_url"]
    if invitation and not re.fullmatch(r"https://testflight\.apple\.com/join/[A-Za-z0-9]+", invitation):
        raise ValueError("testflight_url must be empty or an HTTPS TestFlight public invitation")


def render(lang, values, config, base):
    e = escape
    data = {key: e(value) for key, value in values.items() if isinstance(value, str)}
    site = config["site_url"].rstrip("/")
    data.update(lang=lang, base=e(base), canonical=e(f"{site}/{lang}/"))
    data["alternates"] = "\n  ".join(
        f'<link rel="alternate" hreflang="{language}" href="{e(site)}/{language}/">'
        for language in LANGUAGES
    ) + f'\n  <link rel="alternate" hreflang="x-default" href="{e(site)}/">'
    data["languages"] = "".join(
        f'<a href="{e(base)}/{language}/" lang="{language}" hreflang="{language}"'
        f' aria-label="{name}"' + (' aria-current="page"' if language == lang else '')
        + f'>{language.upper()}</a>' for language, name in LANGUAGES.items()
    )
    data["cta"] = (
        f'<a class="cta" href="{e(config["testflight_url"])}">{e(values["cta_join"])}</a>'
        if config["testflight_url"] else
        f'<button class="cta" type="button" disabled>{e(values["cta_soon"])}</button>'
    )
    # Invitation availability changes the surrounding copy too, not only the button.
    if config["testflight_url"]:
        data["closing_note"] = e(values["available_note"])
    data["principles"] = "".join(f"<span>{e(text)}</span>" for text in values["principles"])
    def story_media(story):
        source = f'{e(base)}/assets/screenshots/{lang}-{story["screen"]}.png'
        poster = (f'<div class="phone motion-poster"><img src="{source}" '
                  f'alt="{e(story["alt"])}" width="1206" height="2622" loading="lazy" decoding="async"></div>')
        if story["screen"] not in motion_screens(lang):
            return poster
        animation = f'{e(base)}/assets/demos/{lang}-{story["screen"]}.mp4'
        return (f'<div class="phone demo"><video muted playsinline preload="none" poster="{source}" '
                f'aria-label="{e(values["capture_motion_alt"] if story["screen"] == "capture" else values["completion_alt"])}" '
                f'width="1206" height="2622" data-src="{animation}"></video>'
                f'<button class="demo-replay" type="button" hidden data-play="{e(values["play_demo"])}" '
                f'data-replay="{e(values["replay_demo"])}">{e(values["replay_demo"])}</button></div>')

    data["stories"] = "".join(
        f'<article class="story-row"><figure class="story-image">{story_media(story)}'
        f'<figcaption>{e(story["caption"])}</figcaption></figure><div class="story-copy">'
        f'<span class="step-number">0{index} /</span><h3>{e(story["title"])}</h3>'
        f'<p>{e(story["body"])}</p><p class="aside">{e(story["aside"])}</p></div></article>'
        for index, story in enumerate(values["stories"], 2)
    )
    data["features"] = "".join(
        f'<article class="feature"><span class="feature-index" aria-hidden="true">0{index}</span>'
        f'<h3>{e(title)}</h3><p>{e(body)}</p></article>'
        for index, (title, body) in enumerate(values["features"], 1)
    )
    data["privacy_points"] = "".join(f"<li>{e(point)}</li>" for point in values["privacy_points"])
    faqs = [list(faq) for faq in values["faqs"]]
    if config["testflight_url"]:
        faqs[0][1] = values["available_answer"]
    data["faqs"] = "".join(f'<details><summary>{e(question)}</summary><p>{e(answer)}</p></details>' for question, answer in faqs)
    return Template((ROOT / "templates/page.html").read_text()).substitute(data)


def build(output=None, config=None, base_path=None):
    output = Path(output) if output else ROOT / "dist"
    config = config or json.loads((ROOT / "config.json").read_text())
    validate_config(config)
    base = urlsplit(config["site_url"]).path.rstrip("/") if base_path is None else base_path.rstrip("/")
    if base and not re.fullmatch(r"(/[A-Za-z0-9_-]+)+", base):
        raise ValueError("base path must contain only URL path segments")
    content = load_content()
    # Explicit asset allowlist: no app sources, documents, test exports or personal data.
    assets = ["app-icon.png", "style.css", "motion.js"] + [f"screenshots/{lang}-{screen}.png" for lang in LANGUAGES for screen in SCREENS]
    assets += [f"demos/{lang}-{screen}.mp4" for lang in LANGUAGES for screen in motion_screens(lang)]
    for asset in assets:
        if not (ROOT / "assets" / asset).is_file():
            raise FileNotFoundError(f"Missing public asset: {asset}")
    allowed = {"index.html", ".nojekyll"} | {f"{lang}/index.html" for lang in LANGUAGES} | {f"assets/{asset}" for asset in assets}
    existing = {str(path.relative_to(output)) for path in output.rglob("*") if path.is_file()}
    if existing - allowed:
        raise ValueError("Output contains unexpected files; use an empty output directory")
    output.mkdir(parents=True, exist_ok=True)
    for asset in assets:
        destination = output / "assets" / asset
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "assets" / asset, destination)
    for lang, values in content.items():
        (output / lang).mkdir(exist_ok=True)
        (output / lang / "index.html").write_text(render(lang, values, config, base), encoding="utf-8")
    (output / "index.html").write_text(render("en", content["en"], config, base), encoding="utf-8")
    (output / ".nojekyll").touch()
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Output directory (default: website/dist)")
    parser.add_argument("--base-path", help="Override URL prefix; use an empty string for a local preview")
    arguments = parser.parse_args()
    print(f"Built website: {build(arguments.output, base_path=arguments.base_path)}")
