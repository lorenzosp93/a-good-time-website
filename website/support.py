"""Shared support copy, static pages and GitHub Issue Forms (no runtime service)."""
from html import escape as e
import json
from pathlib import Path
from string import Template
from urllib.parse import urlencode, quote

ROOT = Path(__file__).resolve().parent
REPOSITORY = 'https://github.com/lorenzosp93/a-good-time-website'
EMAIL = 'support@agoodtime.to'
LANGUAGES = {'en': 'English', 'it': 'Italiano', 'es': 'Español'}
LABELS = {'problem': 'support', 'improvement': 'improvement', 'feature': 'feature-request'}


def load_support():
    # Reuse translation validation without introducing an import cycle at module load.
    from build import shape
    content = {lang: json.loads((ROOT / 'content' / f'support-{lang}.json').read_text()) for lang in LANGUAGES}
    for lang, values in content.items():
        if shape(values) != shape(content['en']):
            raise ValueError(f'Incomplete support translations: {lang}')
        if [category['id'] for category in values['categories']] != list(LABELS):
            raise ValueError(f'Unexpected support categories: {lang}')
    return content


def questions(values, category):
    return [values['surface']] + category['fields'] + [
        values['attachments'] if category['id'] == 'problem' else category['optional_field']
    ]


def email_body(values, category):
    return category['title'] + '\n\n' + '\n\n'.join(question + '\n' for question in questions(values, category))


def issue_form(lang, values, category):
    body = [
        {'type': 'markdown', 'attributes': {'value': values['public_notice'] + '\n\n' + values['privacy'] + f'\n\n[{values["email_action"]}](https://agoodtime.to/{lang}/support/#private)'}},
        {'type': 'dropdown', 'id': 'surface', 'attributes': {'label': values['surface'], 'description': values['surface_hint'], 'options': values['surfaces']}, 'validations': {'required': True}},
    ]
    for index, label in enumerate(category['fields']):
        field = {'type': 'textarea', 'id': f'answer-{index+1}', 'attributes': {'label': label}, 'validations': {'required': True}}
        if category['id'] == 'problem' and index == 3:
            field['type'] = 'input'
            field['attributes']['description'] = values['tech_hint'] + ' ' + values['unknown']
        body.append(field)
    body.append({'type': 'textarea', 'id': 'additional', 'attributes': {'label': questions(values, category)[-1]}, 'validations': {'required': False}})
    if category['id'] == 'problem':
        body[-1]['attributes']['description'] = values['attachments_hint']
    body.append({'type': 'checkboxes', 'id': 'public-consent', 'attributes': {'label': values['title'], 'options': [{'label': values['ack'], 'required': True}]}})
    return {'name': f'{category["title"]} · {LANGUAGES[lang]}', 'description': category['intro'], 'labels': [LABELS[category['id']], 'needs-triage'], 'body': body}


def export_issue_forms(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for lang, values in load_support().items():
        for category in values['categories']:
            # JSON is a strict YAML subset, keeping the build dependency-free.
            (destination / f'{category["id"]}-{lang}.yml').write_text(json.dumps(issue_form(lang, values, category), ensure_ascii=False, indent=2) + '\n')
    config = {'blank_issues_enabled': False, 'contact_links': [
        {'name': 'Private support / Assistenza privata / Soporte privado', 'url': 'https://agoodtime.to/support/#private', 'about': 'Email support without a GitHub account. No public report is required.'}
    ]}
    (destination / 'config.yml').write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')


def render_support(lang, values, common, config, base):
    data = {key: e(value) for key, value in values.items() if isinstance(value, str)}
    site = config['site_url'].rstrip('/')
    data["styles"] = (ROOT / "assets/style.css").read_text()
    data.update(lang=lang, base=e(base), canonical=e(f'{site}/{lang}/support/'), skip=e(common['skip']), language_label=e(common['language_label']), privacy_link=e(common['privacy_link']))
    data['alternates'] = '\n'.join(f'<link rel="alternate" hreflang="{code}" href="{e(site)}/{code}/support/">' for code in LANGUAGES) + f'\n<link rel="alternate" hreflang="x-default" href="{e(site)}/en/support/">'
    data['languages'] = ''.join(f'<a href="{e(base)}/{code}/support/" lang="{code}" hreflang="{code}" aria-label="{name}"' + (' aria-current="page"' if code == lang else '') + f'>{code.upper()}</a>' for code, name in LANGUAGES.items())
    data['existing_url'] = REPOSITORY + '/issues'
    data['email'] = EMAIL
    cards = []
    for category in values['categories']:
        identifier = category['id']
        issue_url = REPOSITORY + '/issues/new?' + urlencode({'template': f'{identifier}-{lang}.yml'})
        mail_url = 'mailto:' + EMAIL + '?' + urlencode({'subject': f'A Good Time — {category["title"]}', 'body': email_body(values, category)}, quote_via=quote)
        prompts = email_body(values, category)
        cards.append(f'<article class="support-card" id="{identifier}"><h2>{e(category["title"])}</h2><p>{e(category["intro"])}</p>'
                     f'<div class="support-actions"><a class="cta" href="{e(issue_url)}" aria-describedby="public-notice">{e(values["public_action"])}</a>'
                     f'<a href="{e(mail_url)}">{e(values["email_action"])}</a></div>'
                     f'<details><summary>{e(values["prompts"])}</summary><p>{e(values["tech_hint"] if identifier == "problem" else values["expectations"])}</p>'
                     f'<pre id="prompts-{identifier}">{e(prompts)}</pre><button type="button" class="copy-button" hidden data-copy="prompts-{identifier}">{e(values["copy_prompts"])}</button></details></article>')
    data['cards'] = ''.join(cards)
    data['faqs'] = ''.join(f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in values['faqs'])
    return Template((ROOT / 'templates/support.html').read_text()).substitute(data)
