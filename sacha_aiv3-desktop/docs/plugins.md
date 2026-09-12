# Plugins

SACHA plugins are user-authored skill files. They live on disk, declare
their permissions in a manifest, and are loaded at startup by
`plugins/loader.py`. Plugins cannot mutate SACHA internals directly — they
talk to the tool registry only.

## Layout

```
plugins/
└── examples/
    ├── weather/
    │   ├── plugin.json
    │   └── plugin.py
    └── system_control/
        ├── plugin.json
        └── plugin.py
```

A real user plugin looks the same — a folder under `plugins/` with a
`plugin.json` manifest and a `plugin.py` entry point.

## Manifest (`plugin.json`)

Required fields:

- `name` — display name shown in the HUD
- `version` — semver string
- `entry` — python module path, e.g. `plugin.py`
- `description` — one-line description for the plugin list
- `permissions` — array of strings; see below

## Permissions

Permissions gate what a plugin is allowed to touch. The plugin loader
enforces these before the plugin runs.

| Permission   | Effect                                                |
| ------------ | ----------------------------------------------------- |
| `network`    | May make outbound HTTP/HTTPS requests                 |
| `filesystem` | May read/write inside `data/notes/` only              |
| `exec`       | May run a subprocess (heavily audited, opt-in)        |
| `microphone` | May request the mic while the plugin is foreground    |
| `camera`     | May request the camera while the plugin is foreground |

A plugin requesting more permissions than the user has approved in the HUD
settings panel will refuse to load.

## Authoring a plugin

1. Create a folder under `plugins/<your_plugin>/`.
2. Write `plugin.json` (see manifest fields above).
3. Write `plugin.py` exposing `register(registry)` — the loader calls this
   once and the plugin attaches its tools to the registry.
4. Restart SACHA, or use the HUD's "Reload plugins" action.
5. See `plugins/examples/weather/` for a minimal example.

## Error isolation

`plugins/sandbox.py` wraps every plugin in a try/except. A thrown exception
logs and disables the plugin for the rest of the session — it does **not**
crash SACHA.

## What plugins are NOT

- Plugins cannot spawn background tasks outside the scheduler.
- Plugins cannot read or write the graph memory store directly; they can
  only emit facts through the extractor API.
- Plugins cannot bridge to messaging platforms; that's its own subsystem
  in `bridges/`.