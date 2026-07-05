# nexus-ui/public

Static assets copied verbatim into the built site by Vite (served from `/`). One file:

- `favicon.svg` — the browser tab icon, referenced by `../index.html`.

Nothing else belongs here unless it must be served at a stable root path without
hashing; app assets that are imported by code live under `../src/` instead.
