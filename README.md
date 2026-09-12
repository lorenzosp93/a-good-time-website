# A Good Time

The public landing page for A Good Time, in English, Italian, and Spanish.

Live site: https://agoodtime.to/

## Develop

```sh
python3 -m unittest discover -s website -p 'test_*.py' -v
python3 website/build.py --base-path ''
python3 -m http.server 8765 --bind 127.0.0.1 --directory website/dist
```

Edit translations in `website/content/`, shared markup in
`website/templates/page.html`, and styles in `website/assets/style.css`.
Use `python3 website/build.py` for the production URL prefix.

Set `testflight_url` in `website/config.json` to the real HTTPS TestFlight
invitation when the beta opens. Buttons and availability copy update together.

The Website workflow checks changes and deploys the default branch to GitHub
Pages. Pages must use GitHub Actions as its source. Only `website/dist` is
published. There are no runtime dependencies, third-party fonts, analytics,
cookies, or automatic email collection. Support drafts open your mail app;
messages are sent only when you choose to send them.

## Support

Use https://agoodtime.to/support/ for public GitHub reports and private email.
Support prompts live in website/content/support-{en,it,es}.json; support.py
generates the localized Issue Forms during the reviewed public export.
Forms apply support, improvement or feature-request plus needs-triage labels.
Maintainers add iPhone, Apple Watch or website labels, link duplicates and close
resolved reports with the relevant release. Obtain permission before publishing
material received privately. No response-time or delivery-date promise is made.

Screenshots show the actual app using synthetic sample data. Capture tooling
is maintained with the app; this repository contains the reviewed public PNGs and completion GIFs.
Demos play once when visible, then offer replay. Reduced-motion visitors choose when to play.
