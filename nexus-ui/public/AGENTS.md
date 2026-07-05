# nexus-ui/public

Static assets copied verbatim into the built site by Vite (served from `/`). One file:

- `favicon.svg` — the browser tab icon, referenced by `../index.html`. It is the Nexus
  mark: the letter N drawn as a network graph, hub node at the crossing point, one
  emerald satellite (palette matches the app: indigo-500/400, emerald-500). Hand-authored
  SVG — edit the shapes directly rather than replacing with raster art.

Nothing else belongs here unless it must be served at a stable root path without
hashing; app assets that are imported by code live under `../src/` instead.
