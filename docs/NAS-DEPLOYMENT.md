# NAS Deployment — Always-On Librarian + Backup Hub

> **Status (2026-05-17):** Architecture plan. Not yet executed — re-read before ordering hardware.

A plan to deploy proactive-librarian on a Synology NAS at the home office, accessible from anywhere via Tailscale. The NAS doubles as the on-prem leg of a 3-2-1 backup posture (Google Drive + iCloud + on-prem).

---

## Why NAS instead of VPS

| Concern | VPS path | NAS + Tailscale path |
|---|---|---|
| PDF storage (currently 18 GB, growing) | Sync to cloud (bandwidth, ongoing) | Lives on NAS directly |
| PDF privacy | On third-party cloud | Stays in your home |
| Mobile access | Public DNS + auth + TLS | Private tailnet, zero public surface |
| Always-on | Yes | Yes |
| Recurring cost | $5-20/mo | $0 (Tailscale free tier) |
| Hardware cost | ~$0 | ~$1,000 upfront |
| Other use cases | None | Time Machine, vault backup, media server, other always-on services |
| Embedding compute | CPU (slow) or remote API (cost/privacy) | NAS CPU (slow but free, nightly batch acceptable) |

The NAS wins as long as you'd buy one anyway for backup. You would.

---

## Hardware

**Recommended:** **Synology DS923+** with 2× WD Red Plus 8 TB drives in RAID1.

| Item | Why | Approx |
|---|---|---|
| Synology DS923+ (4-bay) | Best DSM software polish, first-party Tailscale + Docker (Container Manager), excellent macOS integration | $600 |
| 2× WD Red Plus 8 TB (CMR, NAS-rated) | CMR critical — avoid SMR which kills RAID rebuilds. Plus models are the consumer line; Pro adds vibration tolerance for 5+ bay setups (overkill here). | $200 ea |
| 1× M.2 NVMe SSD (optional, e.g. WD Red SN700 500 GB) | DSM 7.2 supports M.2 as a *storage volume* (not just cache) — useful for the librarian's `.derived/` cache and Docker volumes where small-file IO matters. | $100 |
| Cat 6 cable + UPS (CyberPower CP1500AVRLCD or similar) | UPS is non-negotiable for a NAS that holds your only on-prem backup | $200 |
| **Total** | | **~$1,300** |

Leaves 2 bays empty for future expansion (jump to RAID6 with 4 drives later if storage demand grows).

---

## Architecture

```
                            ┌─────────────────────────────┐
                            │   Phone / iPad / laptop     │
                            │   (anywhere, via Tailscale) │
                            └────────────┬────────────────┘
                                         │ wireguard tunnel
                                         │ (100.x.y.z private IP)
                                         ▼
                            ┌─────────────────────────────┐
                            │   Synology DS923+ NAS       │
                            │   ┌───────────────────────┐ │
                            │   │ Tailscale (package)   │ │
                            │   ├───────────────────────┤ │
                            │   │ Docker (Container     │ │
                            │   │ Manager):             │ │
                            │   │   - librarian-web     │ │
                            │   │   - librarian-ingest  │ │
                            │   │     (scheduled)       │ │
                            │   │   - qmd binary mount  │ │
                            │   ├───────────────────────┤ │
                            │   │ Volumes (BTRFS):      │ │
                            │   │   /volume1/library/   │ │
                            │   │     Research/         │ │
                            │   │     Writing-Research/ │ │
                            │   │   /volume1/derived/   │ │
                            │   │     research/         │ │
                            │   │     writing/          │ │
                            │   ├───────────────────────┤ │
                            │   │ DSM packages:         │ │
                            │   │   Hyper Backup        │ │
                            │   │     → Google Drive    │ │
                            │   │     → Backblaze B2    │ │
                            │   │   Time Machine target │ │
                            │   │   Cloud Sync (iCloud  │ │
                            │   │     mirror via Mac)   │ │
                            │   └───────────────────────┘ │
                            └─────────────────────────────┘
```

The NAS is the **single source of truth for PDFs**. The Mac becomes a client — it accesses the library via Tailscale (over LAN at home, over wireguard when away), drops new PDFs into the NAS shared folder, and consumes citations via the web UI or CLI.

---

## Setup sequence

Order matters: backup before search. The NAS earns its purchase the day backups start; the librarian is the bonus layer.

### Phase 1: Backup foundation (Day 1 — non-negotiable first)

1. **Provision DSM 7.2.** Initial setup wizard, set static IP via router DHCP reservation.
2. **Create storage pool + volume.** RAID1 on the 2× 8 TB drives → ~8 TB usable. BTRFS filesystem (snapshots, integrity checksums).
3. **Create shared folders:**
   - `library/` — PDFs (NEW canonical location, replacing `~/Dev/Dex/06-Resources/Research/` and `Writing-Research/` on the Mac)
   - `vault/` — Dex vault mirror (Hyper Backup target)
   - `time-machine/` — Mac Time Machine target
   - `media/` — future-proofing (Plex, photos, etc.)
   - `cloud-sync/` — Google Drive bidirectional mirror via Cloud Sync package
4. **Install Hyper Backup, configure 3-2-1 posture:**
   - **Local backup:** NAS → Backblaze B2 (the offsite leg, $6/TB/month). Encrypted client-side.
   - **Cloud Sync:** Google Drive ↔ NAS `cloud-sync/` (bidirectional mirror). Existing Google Drive content stays accessible.
   - **iCloud:** can't mirror directly. Workaround — Mac's local `~/Library/Mobile Documents/` is the iCloud cache; rsync that to NAS nightly via launchd.
5. **Time Machine target:** turn on AFP/SMB Time Machine in DSM, point your Mac at it.
6. **Snapshot schedule:** BTRFS snapshots hourly for 24 hours, daily for 30 days, weekly for 12 weeks. Storage cost is near-zero.

At this point the NAS is already valuable, even if you never deploy the librarian.

### Phase 2: Tailscale (Day 1, 10 minutes)

1. Install Synology's official **Tailscale** package from Package Center (it's first-party as of DSM 7.2).
2. Auth with your Tailscale account. NAS gets a tailnet IP like `100.x.y.z` and a magic-DNS name like `nas.tailnet-name.ts.net`.
3. Install Tailscale on phone, iPad, all laptops you might use. Same account = same tailnet.
4. Verify: from phone (cellular, off home wifi), `ping nas.tailnet-name.ts.net` should resolve and respond.

No public DNS, no port forwarding on the home router, no TLS certs to manage. Tailscale handles everything.

### Phase 3: Migrate the PDF library (Day 2)

The Mac is currently the source of truth for `~/Dev/Dex/06-Resources/Research/` (1,378 PDFs, 11 GB) and `Writing-Research/` (29 PDFs, ~600 MB). Move them.

```bash
# From the Mac, over LAN (Tailscale fallback if remote)
rsync -av --progress \
  ~/Dev/Dex/06-Resources/Research/ \
  /Volumes/library/Research/

rsync -av --progress \
  ~/Dev/Dex/06-Resources/Writing-Research/ \
  /Volumes/library/Writing-Research/
```

After verifying integrity (count + sha1 spot-check), update `~/Dev/Dex/.gitignore` to remove the old paths (they're already ignored but cleaner to remove), and decide whether the Mac-side originals stay as a working copy (recommended initially) or are deleted (after a confidence period).

For the Mac client: mount the NAS `library/` share via SMB and point the librarian config at `/Volumes/library/Research/` instead of the local path. The CLI and skill behaviour is unchanged.

### Phase 4: Deploy the librarian container (Day 2)

**`/volume1/docker/librarian/Dockerfile`:**

```dockerfile
FROM python:3.12-slim

# Install Bun for QMD
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl unzip ca-certificates && \
    curl -fsSL https://bun.sh/install | bash && \
    rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.bun/bin:${PATH}"

# Install QMD via Bun
RUN bun install -g qmd

# Install proactive-librarian
RUN pip install --no-cache-dir proactive-librarian fastapi uvicorn jinja2

# Embedding model is downloaded on first use, cached in /root/.cache/qmd
WORKDIR /app
COPY web.py config.yaml ./

EXPOSE 8000
CMD ["uvicorn", "web:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`/volume1/docker/librarian/config.yaml`:**

```yaml
# In-container paths; the docker-compose mounts map them to the NAS volumes
pdf_root: /pdfs/Research
derived_dir: /derived/research/.derived
collection_name: research

# For the writing collection, run a second container with this overridden
# OR pass --pdf-root /pdfs/Writing-Research --collection writing on the CLI
backend:
  type: qmd
  binary: /root/.bun/bin/qmd
  timeout_seconds: 60
```

**`/volume1/docker/librarian/docker-compose.yml`:**

```yaml
services:
  librarian-web:
    build: .
    container_name: librarian-web
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"   # tailnet-only access; NAS exposes it on its tailnet IP
    volumes:
      - /volume1/library:/pdfs:ro                # PDFs read-only from container
      - /volume1/derived:/derived                # derived cache read-write
      - librarian-qmd-cache:/root/.cache/qmd     # embedding model cache
    environment:
      - LIBRARIAN_PDF_ROOT=/pdfs/Research
      - TZ=Europe/Rome

  librarian-ingest:
    build: .
    container_name: librarian-ingest
    restart: "no"
    profiles: ["batch"]                          # only runs when explicitly invoked
    volumes:
      - /volume1/library:/pdfs:ro
      - /volume1/derived:/derived
      - librarian-qmd-cache:/root/.cache/qmd
    command: ["sh", "-c", "librarian ingest --pdf-root /pdfs/Research --collection research && librarian ingest --pdf-root /pdfs/Writing-Research --collection writing"]

volumes:
  librarian-qmd-cache:
```

**`/volume1/docker/librarian/web.py`** (minimal FastAPI + HTMX, ~100 lines):

```python
"""Tiny mobile-friendly web UI over the librarian's QMD backend."""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from proactive_librarian.config import load_config
from proactive_librarian.query import run_qmd_query, parse_result_path
from pathlib import Path

app = FastAPI(title="Librarian")
config = load_config(explicit_path=Path("/app/config.yaml"))

PAGE = """<!doctype html>
<html><head>
  <title>Librarian</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; max-width: 720px;
           margin: 1.5rem auto; padding: 0 1rem; }
    input[type=search] { width: 100%; font-size: 1.1rem; padding: .6rem;
                          border: 1px solid #ccc; border-radius: 6px; }
    .hit { border-top: 1px solid #eee; padding: .8rem 0; }
    .cite { font-weight: 600; }
    .score { color: #888; font-size: .85rem; }
    blockquote { color: #444; border-left: 3px solid #ddd;
                  margin: .4rem 0 0 0; padding: 0 .8rem; }
    select { padding: .4rem; border-radius: 6px; }
  </style>
</head><body>
  <h1>Librarian</h1>
  <form hx-get="/search" hx-target="#results" hx-trigger="submit, change from:#col">
    <input type="search" name="q" placeholder="Query the library..." autofocus>
    <p>
      Collection:
      <select id="col" name="collection">
        <option value="research">research (third-party reading)</option>
        <option value="writing">writing (your own work)</option>
      </select>
    </p>
  </form>
  <div id="results"></div>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE


@app.get("/search", response_class=HTMLResponse)
def search(q: str = "", collection: str = "research", n: int = 5) -> str:
    if not q.strip():
        return ""
    raw = run_qmd_query(q, config, limit=n * 3)
    valid = [r for r in raw if parse_result_path(r)[1] is not None][:n]
    if not valid:
        return "<p>No results.</p>"
    parts = []
    for r in valid:
        pdf_rel, page = parse_result_path(r)
        snippet = (r.get("snippet") or "").replace("\n", " ")[:320]
        score = r.get("score", 0.0)
        parts.append(
            f'<div class="hit">'
            f'<div class="cite">{Path(pdf_rel).name}:p.{page}'
            f'<span class="score"> · {score:.2f}</span></div>'
            f'<blockquote>{snippet}</blockquote></div>'
        )
    return "".join(parts)
```

**Bring it up:**

```bash
ssh nas
cd /volume1/docker/librarian
docker compose up -d librarian-web
docker compose run --rm librarian-ingest    # initial full ingest (40-90 min CPU-bound)
```

Web UI is now reachable at `http://nas.tailnet-name.ts.net:8000/` from any tailnet member.

### Phase 5: Mobile access

1. Install Tailscale app on iOS/Android, sign in.
2. Bookmark `http://nas.tailnet-name.ts.net:8000/` in mobile browser (or add to home screen as a PWA-ish shortcut).
3. Done. Search from anywhere. Citations are `file.pdf:p.N` — you read them off the screen, copy/paste into Drafts or your in-progress doc.

### Phase 6: Periodic ingest

Schedule via Synology's Task Scheduler (DSM → Control Panel → Task Scheduler):

- **Nightly at 03:00:** `docker compose run --rm librarian-ingest` (incremental sha1-based, runs only for new/changed PDFs — usually <1 minute when nothing changed)
- **Weekly Sunday at 04:00:** `qmd update && qmd embed` inside the container, to refresh QMD's index and pick up any deferred embeddings

---

## Synology-specific gotchas to know in advance

1. **DSM Tailscale package vs Docker Tailscale sidecar.** Use the **DSM package** — it puts the *NAS itself* on the tailnet, so all DSM services (file shares, Hyper Backup web UI, Container Manager UI) become reachable via the tailnet IP. The sidecar pattern would only expose individual containers.
2. **Docker Container Manager ≠ docker CLI.** Synology's GUI wraps docker compose but sometimes lags behind upstream. SSH in and use the real `docker compose` for anything non-trivial — the GUI is fine for inspecting state.
3. **CPU embedding will be slow on the DS923+ Ryzen R1600** (~4-5x slower than your Mac's Neural Engine). 28k chunks ≈ 90-120 minutes vs your Mac's 23. Run as overnight batch, never blocking.
4. **BTRFS snapshots eat space on a churning `.derived/` cache.** Either keep `.derived/` on a separate volume excluded from snapshots, OR set a short snapshot retention on `/volume1/derived/` specifically.
5. **SMB file timestamp drift between macOS and Synology** can cause sha1-skip logic to think files changed when they didn't. Mitigation: the librarian's sha1 check is *content-based*, not mtime-based, so this is moot for us — but it can confuse other tools (rsync, Time Machine).
6. **Embedding model storage.** `embeddinggemma-300M-Q8_0.gguf` is ~330 MB. Cached in the named volume; survives container rebuilds.

---

## Cost summary

| Recurring | Monthly |
|---|---|
| Tailscale (free tier, up to 100 devices) | $0 |
| Backblaze B2 (for offsite encrypted backup, ~500 GB to start) | ~$3 |
| Electricity (DS923+ draws ~13 W idle, ~30 W active) | ~$2 |
| **Recurring total** | **~$5/mo** |

vs the VPS path (~$10-20/mo) — break-even at year 3-5 on the hardware, with the NAS doing more.

---

## Open decisions to make before ordering

1. **8 TB or 12 TB drives?** 8 TB is plenty for the foreseeable use case (PDFs + vault + Time Machine + media), 12 TB doubles your headroom for ~$80 more per drive. Lean toward 12 if you intend to centralise more media (photos, video archive).
2. **Add an M.2 NVMe?** Worth it if Docker container builds + `.derived/` IO bother you. Skippable for v1.
3. **UPS sizing.** CyberPower CP1500AVRLCD (1500 VA) gives ~30 minutes runtime for a NAS-only load. Bigger UPS only matters if you'd want the Mac or other devices powered through outages too.
4. **Public web UI vs tailnet-only.** Plan is tailnet-only. If you ever want to share a citation lookup with a non-tailnet collaborator (Sjors, Project X folks), think about a separate read-only endpoint behind Cloudflare Access — different decision, future ADR.

---

## What this doesn't address (deferred)

- **Multi-user / collaborator access.** Single-user only. Adding RBAC is a separate project.
- **Auto-ingest on PDF drop.** Could be done via Synology Universal Search hooks or a filesystem watcher (inotify). Out of scope for v1; nightly cron is fine.
- **Mobile PDF viewing.** Citations point at PDFs that live on the NAS — to actually *view* the PDF on your phone, you'd add the Synology Drive client (or just open the SMB share). The librarian's job is finding the citation, not displaying the PDF.

---

## Sequence checklist (when you're ready)

- [ ] Order DS923+ + 2× drives + UPS
- [ ] Phase 1: backup foundation (Hyper Backup, Time Machine, Cloud Sync, snapshots)
- [ ] Phase 2: Tailscale on NAS + phone + laptops
- [ ] Phase 3: rsync PDF library Mac → NAS, verify integrity
- [ ] Phase 4: deploy librarian container, run initial full ingest
- [ ] Phase 5: bookmark mobile URL, smoke-test from cellular
- [ ] Phase 6: Task Scheduler cron jobs for nightly ingest + weekly reindex/embed
- [ ] Update `proactive-librarian.yaml` on the Mac to point at the SMB-mounted NAS path (so local CLI still works)
- [ ] Update the Dex skill's path in `~/Dev/Dex/.claude/skills/librarian/` to match (same change)
- [ ] Document the new canonical PDF path in the Recipe Library

---

## Links

- Tailscale on Synology DSM: https://tailscale.com/kb/1131/synology
- Synology Docker / Container Manager: https://www.synology.com/en-us/dsm/feature/container-manager
- Hyper Backup → Backblaze B2: https://kb.synology.com/en-us/DSM/help/HyperBackup/
- BTRFS snapshots in DSM: https://kb.synology.com/en-us/DSM/help/SnapshotReplication/
- proactive-librarian itself: README.md, docs/PYPI-PUBLISH.md, docs/adr/
