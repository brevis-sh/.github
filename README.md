# .github

The organisation's front page. GitHub renders [`profile/README.md`](profile/README.md)
at the top of [github.com/brevis-sh](https://github.com/brevis-sh).

The images in `profile/assets/` are SVGs with every glyph as a path: GitHub
shows README images inside `<img>` and through a proxy, where an SVG cannot
load a web font, and a banner set in a font the viewer may not have is a
banner that looks different on every machine. Each carries the site's dark
ground (`#141711`), so one file works in both GitHub themes. They are generated
by `profile/assets/gen.py` from IBM Plex Mono and IBM Plex Sans, the project's
two typefaces ([`docs/BRAND.md`](https://github.com/brevis-sh/brevis/blob/master/docs/BRAND.md)),
and the site's icon sprite.

```bash
python3 -m venv .venv && .venv/bin/pip install fonttools uharfbuzz
.venv/bin/python profile/assets/gen.py   # needs the Plex TrueType files; the script says where
```

Everything else about the project lives in [brevis-sh/brevis](https://github.com/brevis-sh/brevis).
