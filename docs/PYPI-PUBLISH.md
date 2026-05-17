# PyPI Publish — Memo for When the Time Is Right

> **Status (2026-05-17):** Not yet published. This memo captures the full publishing playbook for the moment v0.1.x feels stable enough to ship. Re-read top-to-bottom before doing anything.

---

## When to revisit this

You're ready to publish when **all** of the following are true:

- [ ] The CLI has been used against your real research library for at least two weeks.
- [ ] The known sharp edges (encrypted-PDF quirks, taxonomy edge cases, QMD setup friction for newcomers) have surfaced and been addressed in code or docs.
- [ ] The `CHANGELOG.md` has at least one or two follow-up entries beyond the initial `0.1.0`.
- [ ] You're comfortable with `proactive-librarian` becoming **permanently your name** on PyPI (first-come-first-served, no take-backs).
- [ ] You're comfortable with **every published version being immutable** (you can yank/hide but not replace or delete).

If any of those is "no", don't publish yet.

---

## What PyPI is and why it matters

PyPI (Python Package Index) is the central registry behind `pip install <name>`. Once `proactive-librarian` is on PyPI, anyone can:

```bash
pip install proactive-librarian
```

…and immediately have the `librarian` CLI on their PATH. No GitHub clone, no `pip install -e .`, no Python-package mechanics. That's the value proposition. Without it, the project is "clone the repo and run the scripts" — fine for personal use, friction-heavy for anyone else.

---

## Prerequisites

1. **PyPI account** at https://pypi.org/account/register/ — free, takes 2 minutes. Separate from GitHub.
2. **TestPyPI account** at https://test.pypi.org/account/register/ — the staging sandbox. Same email is fine. Use it once before going live.
3. **2FA on both accounts.** PyPI requires 2FA for uploads as of 2024.
4. **Local build tools:**
   ```bash
   pip install build twine
   ```
5. **The `pyproject.toml` you already have.** It's PyPI-ready. No edits needed for v0.1.0.

---

## Path A — Manual publish (one-time, 5 minutes)

Good for: the first release, learning what the workflow does, situations where you don't want CI involvement.

```bash
cd ~/Dev/proactive-librarian

# 1. Build the package
python -m build
# Produces dist/proactive_librarian-0.1.0.tar.gz + .whl

# 2. Sanity-check the metadata
twine check dist/*

# 3. Publish to TestPyPI first (NEVER skip this on first publish)
twine upload --repository testpypi dist/*

# 4. Verify the install actually works from TestPyPI
python -m venv /tmp/test-install && source /tmp/test-install/bin/activate
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            proactive-librarian
librarian --version    # should print "librarian 0.1.0"
deactivate && rm -rf /tmp/test-install

# 5. Publish to real PyPI
twine upload dist/*
```

After step 5, `pip install proactive-librarian` works worldwide within ~30 seconds (CDN propagation).

Twine will prompt for credentials. You can either type them each time, or store an API token in `~/.pypirc`. Use API tokens, not your password.

---

## Path B — GitHub Actions + Trusted Publisher (recommended once you've done it manually once)

Good for: every release after the first. Modern, secure (no API tokens stored anywhere), repeatable, audit-trail in CI logs.

How it works: PyPI's "Trusted Publisher" feature lets you register a GitHub repo + workflow as authorised to upload via OpenID Connect (OIDC). No tokens involved. A git tag like `v0.2.0` triggers the workflow, which builds + uploads automatically.

### Setup (one-time)

1. On PyPI, go to your project → **Publishing** → **Add a new pending publisher** (works even before the package exists). Fill in:
   - PyPI Project Name: `proactive-librarian`
   - Owner: `davidorban`
   - Repository name: `proactive-librarian`
   - Workflow name: `publish.yml`
   - Environment name: `pypi` (optional but recommended)

2. Add this workflow to the repo at `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  push:
    tags: ['v*.*.*']

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write           # required for OIDC
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

3. (Optional) Add a parallel workflow for TestPyPI on `release/*` branches so you can stage without tagging.

### Releasing thereafter

```bash
# Bump version in pyproject.toml (or use setuptools-scm for auto-derivation)
git commit -am "chore: bump to v0.2.0"
git tag v0.2.0
git push --tags
```

GitHub Actions takes over from there. Total elapsed time: ~90 seconds.

---

## Catches worth knowing

1. **The name is permanently yours once claimed.** First-come-first-served. If `proactive-librarian` matters to you, claim it early (publish v0.0.1 today, even as a placeholder). As of 2026-05-17 the name was free.

2. **Uploads are immutable.** You cannot replace a file. To fix a bug in v0.1.0 you ship v0.1.1. PyPI does allow **yanking** (hiding a version from `pip install` without deleting it) for genuinely broken releases.

3. **Version bumps are mandatory per upload.** Manage manually via the `version = "0.1.0"` line in `pyproject.toml`, OR use [setuptools-scm](https://setuptools-scm.readthedocs.io/) to derive automatically from git tags (recommended once you're on Path B — eliminates the bump-then-tag drift).

4. **Dependencies must also be on PyPI** to install cleanly. Your current deps (`pypdf`, `cryptography`, `tqdm`, `PyYAML`) are all there. QMD is a **separate concern** — it's a binary the user installs independently, not a pip dependency. The README already points at the QMD repo; that's the right pattern (do not bundle non-pip binaries inside a Python package).

5. **PyPI renders your `README.md` as the project description.** Your current README will render correctly (PyPI supports GitHub-flavoured markdown). Preview it locally with `twine check dist/*`.

6. **Long description content type** is auto-detected from `pyproject.toml` thanks to `readme = "README.md"`. No extra config needed.

7. **No undo.** You can yank versions and you can request a project name release if you absolutely must, but in practice plan on the name being permanent.

8. **`pip install` cache + CDN propagation.** New uploads are visible to `pip install` within ~30 seconds globally. The PyPI web UI sometimes lags by a few minutes.

---

## Pre-publish checklist (run through this before `twine upload dist/*`)

- [ ] All tests pass: `pytest`
- [ ] `python -m build` produces both `.tar.gz` and `.whl` in `dist/` without warnings
- [ ] `twine check dist/*` is green
- [ ] `pyproject.toml` version matches the git tag you intend to push (`v0.X.Y` ↔ `version = "0.X.Y"`)
- [ ] `CHANGELOG.md` has an entry for the new version
- [ ] README links work (PyPI is unforgiving about relative links — use absolute GitHub URLs)
- [ ] LICENSE is present and matches the pyproject `license` field
- [ ] You've installed-from-TestPyPI into a clean venv and run `librarian --version` and a real query
- [ ] You're not about to publish a version that contains debug-only code, hardcoded credentials, or anything personal

---

## After-publish maintenance

- **Pin a CI matrix.** GitHub Actions matrix-test across Python 3.9 / 3.10 / 3.11 / 3.12 / 3.13 — that's what `pyproject.toml` advertises support for.
- **Monthly dependency review.** `pip list --outdated` against the dev environment. Update `pyproject.toml` constraints if any deps have known CVEs.
- **Release notes hygiene.** Every PyPI release should have a matching GitHub Release with a copy of the CHANGELOG entry. The GitHub Actions release flow can automate this.
- **Watch the GitHub issues.** Most bug reports from `pip install` users land there, not via email.

---

## Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-17 | **Defer publish** | Want real-world usage data on the standalone before committing the name. The PyPI name reservation can also be done as a v0.0.1 placeholder if squatting becomes a concern. |
| _(future)_ | _(record decisions here as they happen)_ | |

---

## Useful links

- PyPI account signup: https://pypi.org/account/register/
- TestPyPI account signup: https://test.pypi.org/account/register/
- Trusted Publisher docs: https://docs.pypi.org/trusted-publishers/
- `setuptools-scm` (auto-version from git tags): https://setuptools-scm.readthedocs.io/
- `twine` docs: https://twine.readthedocs.io/
- `pyproject.toml` reference: https://packaging.python.org/en/latest/specifications/pyproject-toml/
- QMD (the search backend this project ships with): https://github.com/eatonphil/qmd
