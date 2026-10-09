# MoviePilot-Plugins

**English** | [简体中文](./README.md)

A personal MoviePilot V3 plugin marketplace repository.

MoviePilot reads a GitHub repository's `main` branch index via the `PLUGIN_MARKET` config;
multiple addresses are separated by commas.

## Plugins

| Plugin | Description |
| --- | --- |
| [MyLibrary](plugins.v3/mylibrary) | Browse your local media library from the left nav: NFO metadata plus a local image poster wall. Hover for a synopsis, click through for director/cast/resolution/file list, with direct links to TheMovieDb / IMDb / Douban |

## How to subscribe

In MoviePilot go to:

**System Settings → Plugin Market → Plugin Repository**, and enter this repository's address:

```text
https://raw.githubusercontent.com/kyf778/MoviePilot-Plugins/main
```

Save, refresh the plugin market, and "MyLibrary" will be available to install.

> You can also edit `PLUGIN_MARKET` directly (System Settings → Plugin → Plugin Repository).
> Separate multiple addresses with commas, for example:
> `https://raw.githubusercontent.com/jxxghp/MoviePilot-Plugins/main,https://raw.githubusercontent.com/kyf778/MoviePilot-Plugins/main`

## Usage

After installing, fill in the plugin settings:

- **Enable**: turn the plugin on
- **Media library directory**: e.g. `/media/Videos/Movies` (one subdirectory per movie,
  containing its NFO and images)
- **Poster size**: `medium` / `small` / `large`

The plugin adds a "MyLibrary" entry under the "Media Organize" group in the left nav.

### Supported directory layout

```text
Videos/
├── Mission Impossible (1996)/
│   ├── Mission Impossible (1996).nfo   # required: metadata
│   ├── poster.jpg                      # portrait poster (required)
│   ├── landscape.jpg                   # landscape backdrop (optional, falls back to poster)
│   └── Mission Impossible (1996).mkv   # video file
└── Quantum of Solace (2008)/
    └── ...
```

Image filenames accept the common Jellyfin / Emby / TinyMediaManager conventions, with this
resolution priority:

| Purpose | Candidate filenames (in priority order) |
| --- | --- |
| Portrait poster | `poster.jpg` → `folder.jpg` → `cover.jpg` |
| Landscape backdrop | `landscape.jpg` → `thumb.jpg` |

> **Note**: this plugin deliberately does not use `fanart.jpg` / `backdrop.jpg` as the detail
> page backdrop. For many movies those files are "gun barrel / tunnel" first-person shots,
> which produce a bright circular blob in the centre when used as a background — it looks bad.

### Douban links (filled in automatically)

NFO files usually have no `<doubanid>`, and MoviePilot's Douban API can't supply the id
either, so the only route is Douban web search — and Douban's anti-scraping is strict.
The plugin ships a background thread that fills these in automatically, so **no action is
needed after new movies are added**:

- only queries entries that have an NFO but no Douban ID; cached results are never re-requested
- 1.2 seconds between movies, serial requests (matching Douban's tolerance)
- on a "searching too frequently" response it cools down for 30 minutes, then continues
- results are written to `<media library dir>/.douban_ids.json` (atomic replace, so the cache
  can't be corrupted)

The settings page has an "auto-fill Douban IDs" toggle to turn this off. With it off you can
still run the script manually:

```bash
python3 tools/fetch_douban_ids.py /media/Videos/Movies
```

- the script is re-runnable: cached entries are skipped, and an interrupted run resumes
- its cache format matches what the plugin writes, so the two can be mixed
- with no cache, the detail page's Douban link falls back to a Douban search page

## Repository layout

```text
MoviePilot-Plugins/
├── plugins.v3/              # V3 plugins (directory name must be the lowercased main class name)
│   └── mylibrary/
│       ├── __init__.py      # plugin backend
│       ├── vite.config.js   # federation build config (the official CSS gate relies on it to detect the plugin)
│       └── dist/            # Vue federation build output
├── icons/                   # plugin icons
├── tools/                   # helper scripts
├── docs/                    # plugin docs
├── tests/
│   ├── run.py               # regression entry point (runs grouped by generation)
│   └── v3/mylibrary/        # V3 plugin tests
├── .github/
│   ├── scripts/             # gates and check scripts (incl. files vendored from upstream)
│   └── workflows/           # CI and Release
├── package.v3.json          # V3 plugin market index (the one actually used)
├── package.json             # legacy index placeholder, see below
└── package.v2.json          # V2 generation index placeholder
```

### About the version numbers in the three index files

The official version gate requires **V3 version = legacy version major + 1** (a major bump).
This plugin is a V3-only implementation, so the legacy indexes are marked `"v3": false` to
exclude them:

| File | Version | Purpose |
|---|---|---|
| `package.v3.json` | `3.3.0` | the index a V3 host actually reads |
| `package.v2.json` | `2.0.0` + `"v3": false` | V2 placeholder, so a V2 host recognises and skips it |
| `package.json` | `2.0.0` + `"v3": false` | legacy placeholder |

⚠️ **Do not change the version in `package.json` / `package.v2.json` to `3.3.0`** — that
trips the official gate (the V3 version must be exactly one higher than the legacy version).
When changing versions, consider all three files together.

## Development

```bash
cd plugins.v3/mylibrary
pnpm install
pnpm build          # output goes to dist/assets
```

Run the unified pre-commit check (Python compile + version gate + CSS gate + privacy scan +
unit tests):

```bash
python .github/scripts/preflight.py
```

Or just the tests:

```bash
python tests/run.py
```

> The version and CSS checks in `preflight.py` **call the files vendored from the official
> repository directly** (`.github/scripts/check_plugin_versions.py`,
> `check_federation_css.py`), so the decision logic matches official CI with no
> reimplementation. See [CONTRIBUTING.md](CONTRIBUTING.md).

This repository's CI (`.github/workflows/ci.yml`) runs the gates and tests on every push and
PR. The Release workflow (`release.yml`) packages the plugin directory into
`MyLibrary_v<version>.zip` and publishes it to Releases when `package.v3.json` changes. Tests
use local temp directories only and never touch the network.

Before committing, make sure:

- `plugin_version`, the `version` in `package.v3.json`, and the newest `history` entry agree
- the current version is at the top of the history, the rest in descending semver order
- the plugin directory name is the lowercased main class name (`MyLibrary` → `mylibrary`)
- **do not ship `__federation_shared_vuetify/styles-*.css`** — federated components share the
  same `document` as the host, so global Vuetify styles leak into the host UI. The postcss
  filter in `vite.config.js` drops styles coming from `node_modules/vuetify`; don't delete it
  when touching the build config

## Disclaimer

The plugins here are personal tools and are not affiliated with MoviePilot officially. Review
the code for safety before using it.

Official MoviePilot repository: [jxxghp/MoviePilot-Plugins](https://github.com/jxxghp/MoviePilot-Plugins)
