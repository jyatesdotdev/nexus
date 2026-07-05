// EDUCATIONAL NOTE: A Barrel Makes the Folder the Unit of API
// Consumers write `import { Card, Badge } from './ui'` and never learn how
// this directory is laid out — files can be split or renamed without touching
// call sites, and "is it exported from the barrel?" becomes the line between
// the folder's public surface and its internals. The honest caveat: barrels
// have a cost at scale (importing one symbol parses the whole barrel graph,
// and careless ones breed circular imports), which is why this stays a small,
// leaf-level barrel of four sibling primitives rather than an app-wide
// re-export hub.
export * from './Card'
export * from './Badge'
export * from './Button'
export * from './Input'
