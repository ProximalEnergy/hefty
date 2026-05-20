#!/usr/bin/env node
// Conformance checker for the Bulletproof React (Proximal variant).
// Source of truth:
// .claude/skills/bulletproof-react-feature-structure/SKILL.md (canonical).
// Mirrored at:
//   - .agents/skills/bulletproof-react-feature-structure/SKILL.md (Codex CLI)
//   - web-app/.cursor/rules/bulletproof-react-feature-structure.mdc (Cursor)
//
// Walks src/features/<group>/<feature>/ and asserts:
//   1. Feature folder is kebab-case.
//   2. Group folder is kebab-case.
//   3. Subfolders are limited to the allowed set.
//   4. Subfolder names are kebab-case.
//   5. Feature roots do not contain barrel files.
//   6. File naming matches the convention per subfolder.
//   7. Inside a feature, no @/features/<other>/... cross-feature imports.
//   8. From outside features, imports may reach only route entry files.
//
// Tool-agnostic: cares about code, not which agent wrote it.
// Exit codes: 0 = pass, 1 = violations, 2 = script error.
import { readFile, readdir, stat } from 'node:fs/promises'
import { dirname, join, relative, resolve } from 'node:path'

const ROOT = process.cwd()
const FEATURES_DIR = 'src/features'
const SRC_DIR = 'src'

const ALLOWED_SUBFOLDERS = new Set([
  'components',
  'hooks',
  'queries',
  'routes',
  'types',
  'utils',
  'views',
])

const KEBAB = /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/
const PASCAL = /^[A-Z][A-Za-z0-9]*$/
const USE_KEBAB = /^use-[a-z0-9]+(-[a-z0-9]+)*$/

const violations = []
const warnings = []
let featureCount = 0

const push = (rule, file, message) =>
  violations.push({ rule, file: relative(ROOT, file), message })
const warn = (rule, file, message) =>
  warnings.push({ rule, file: relative(ROOT, file), message })

async function isDir(p) {
  try {
    const s = await stat(p)
    return s.isDirectory()
  } catch {
    return false
  }
}

async function walkSourceFiles(dir, fn) {
  const entries = await readdir(dir, { withFileTypes: true })
  for (const e of entries) {
    const p = join(dir, e.name)
    if (e.isDirectory()) {
      await walkSourceFiles(p, fn)
    } else if (e.isFile() && /\.(ts|tsx)$/.test(e.name)) {
      await fn(p)
    }
  }
}

function* extractImports(source) {
  // Catches `from '...'`, side-effect `import '...'`, and dynamic `import('...')`.
  // We rebuild the source minus comments + string literals, then match raw quoted
  // specifiers in the import-statement positions only.
  const cleaned = source
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:])\/\/[^\n]*/g, '$1')
  const re = /(?:from\s+|import\s+|import\(\s*)['"]([^'"]+)['"]/g
  let m
  while ((m = re.exec(cleaned)) !== null) yield m[1]
}

function isInsideFeature(absPath, features) {
  // Returns the matching feature if absPath is inside one, else null.
  for (const f of features) {
    if (absPath === f.path || absPath.startsWith(f.path + '/')) return f
  }
  return null
}

async function findFeatures() {
  const featuresPath = join(ROOT, FEATURES_DIR)
  if (!(await isDir(featuresPath))) {
    console.error(`error: ${FEATURES_DIR} not found (cwd: ${ROOT})`)
    process.exit(2)
  }
  const groups = await readdir(featuresPath, { withFileTypes: true })
  const features = []
  for (const g of groups) {
    if (!g.isDirectory()) continue
    if (!KEBAB.test(g.name)) {
      push(
        'group-kebab-case',
        join(featuresPath, g.name),
        `group folder "${g.name}" is not kebab-case`,
      )
    }
    const groupPath = join(featuresPath, g.name)
    const entries = await readdir(groupPath, { withFileTypes: true })
    for (const e of entries) {
      if (!e.isDirectory()) continue
      features.push({
        group: g.name,
        name: e.name,
        path: join(groupPath, e.name),
        importRoot: `@/features/${g.name}/${e.name}`,
      })
    }
  }
  return features
}

async function checkFeatureShape(feature) {
  if (!KEBAB.test(feature.name)) {
    push(
      'feature-kebab-case',
      feature.path,
      `feature folder "${feature.name}" is not kebab-case`,
    )
  }

  const entries = await readdir(feature.path, { withFileTypes: true })
  const dirNames = entries.filter((e) => e.isDirectory()).map((e) => e.name)
  const fileNames = entries.filter((e) => e.isFile()).map((e) => e.name)

  for (const d of dirNames) {
    if (!ALLOWED_SUBFOLDERS.has(d)) {
      push(
        'subfolder-allowlist',
        join(feature.path, d),
        `subfolder "${d}" is not in the allowed set ` +
          `{ ${[...ALLOWED_SUBFOLDERS].join(', ')} }`,
      )
    }
    if (!KEBAB.test(d)) {
      push(
        'subfolder-kebab-case',
        join(feature.path, d),
        `subfolder "${d}" is not kebab-case`,
      )
    }
  }

  // Stray top-level files: only optional README.md belongs at the feature root.
  for (const f of fileNames) {
    if (f === 'README.md') continue
    if (f === 'index.ts') {
      push(
        'no-feature-root-barrel',
        join(feature.path, f),
        `feature root index.ts barrels are not allowed`,
      )
      continue
    }
    warn(
      'feature-root-stray-file',
      join(feature.path, f),
      `unexpected file at feature root; consider moving into one of ` +
        `the allowed subfolders`,
    )
  }
}

async function checkFileNaming(feature) {
  const entries = await readdir(feature.path, { withFileTypes: true })
  for (const sub of entries) {
    if (!sub.isDirectory() || !ALLOWED_SUBFOLDERS.has(sub.name)) continue
    const subPath = join(feature.path, sub.name)
    await walkSourceFiles(subPath, async (filePath) => {
      const fname = filePath.split('/').pop()
      const isTsx = fname.endsWith('.tsx')
      const isTs = fname.endsWith('.ts') && !fname.endsWith('.d.ts')
      if (!isTsx && !isTs) return
      const base = fname.replace(/\.tsx?$/, '')

      // .tsx in routes/views/components → PascalCase (component-exporting files)
      if (
        isTsx &&
        (sub.name === 'routes' ||
          sub.name === 'views' ||
          sub.name === 'components')
      ) {
        if (!PASCAL.test(base)) {
          push(
            'file-naming-pascal-tsx',
            filePath,
            `${sub.name}/*.tsx must be PascalCase ("${base}.tsx")`,
          )
        }
      }

      // hooks/*.ts and queries/*.ts → use-<kebab>.ts (queries are data hooks)
      if (isTs && (sub.name === 'hooks' || sub.name === 'queries')) {
        if (!USE_KEBAB.test(base)) {
          push(
            'file-naming-use-hook',
            filePath,
            `${sub.name}/*.ts must match use-<kebab>.ts ("${base}.ts")`,
          )
        }
      }

      // .ts files in any other allowed subfolder → kebab-case
      // (rule from .mdc: "kebab-case for everything else")
      if (
        isTs &&
        (sub.name === 'utils' ||
          sub.name === 'types' ||
          sub.name === 'components' ||
          sub.name === 'views' ||
          sub.name === 'routes')
      ) {
        if (!KEBAB.test(base)) {
          push(
            'file-naming-kebab-ts',
            filePath,
            `${sub.name}/*.ts must be kebab-case ("${base}.ts")`,
          )
        }
      }
    })
  }
}

async function checkInternalImports(feature, allFeatures) {
  await walkSourceFiles(feature.path, async (filePath) => {
    const source = await readFile(filePath, 'utf-8')
    for (const spec of extractImports(source)) {
      // ----- Absolute @/features/... imports -----
      if (spec.startsWith('@/features/')) {
        if (spec === feature.importRoot) {
          warn(
            'self-feature-root-absolute-import',
            filePath,
            `absolute import of own feature root "${spec}"; ` +
              `prefer relative imports inside the feature`,
          )
          continue
        }
        if (spec.startsWith(feature.importRoot + '/')) {
          warn(
            'self-deep-absolute-import',
            filePath,
            `deep absolute import "${spec}" into own feature; prefer relative imports`,
          )
          continue
        }
        push(
          'no-cross-feature-import',
          filePath,
          `cross-feature import "${spec}" — features must not import ` +
            `from other features`,
        )
        continue
      }

      // Relative imports must not escape into another feature.
      if (spec.startsWith('./') || spec.startsWith('../')) {
        const resolved = resolve(dirname(filePath), spec)
        const otherFeature = isInsideFeature(resolved, allFeatures)
        if (otherFeature && otherFeature.path !== feature.path) {
          push(
            'no-cross-feature-import-relative',
            filePath,
            `relative import "${spec}" resolves into feature ` +
              `"${otherFeature.group}/${otherFeature.name}" — features ` +
              `must not import from other features`,
          )
        }
      }
    }
  })
}

async function checkExternalDeepImports(features) {
  const featureRoots = features.map((f) => ({
    root: f.importRoot,
    prefix: f.importRoot + '/',
    path: f.path,
  }))

  const isRouteEntryImport = (importPath) =>
    /^routes\/[A-Z][A-Za-z0-9]*Route$/.test(importPath)

  // Walk the whole src/ tree EXCEPT each feature's own internals.
  const featurePaths = new Set(features.map((f) => f.path))
  const srcRoot = join(ROOT, SRC_DIR)

  async function walk(dir) {
    const entries = await readdir(dir, { withFileTypes: true })
    for (const e of entries) {
      const p = join(dir, e.name)
      if (e.isDirectory()) {
        if (featurePaths.has(p)) continue
        await walk(p)
      } else if (
        e.isFile() &&
        /\.(ts|tsx)$/.test(e.name) &&
        !e.name.endsWith('.d.ts')
      ) {
        const source = await readFile(p, 'utf-8')
        for (const spec of extractImports(source)) {
          // ----- Absolute @/features/... -----
          if (spec.startsWith('@/features/')) {
            for (const { root, prefix } of featureRoots) {
              if (spec === root) {
                push(
                  'no-feature-barrel-import',
                  p,
                  `feature root import "${spec}" resolves to a barrel`,
                )
                break
              }
              if (spec.startsWith(prefix)) {
                if (isRouteEntryImport(spec.slice(prefix.length))) break
                push(
                  'no-deep-feature-import',
                  p,
                  `deep import "${spec}" reaches into feature internals; ` +
                    `import route entry files only`,
                )
                break
              }
            }
            continue
          }
          // Relative imports must not land inside feature internals.
          if (spec.startsWith('./') || spec.startsWith('../')) {
            const resolved = resolve(dirname(p), spec)
            for (const { path: fpath } of featureRoots) {
              if (resolved === fpath) {
                push(
                  'no-feature-barrel-import-relative',
                  p,
                  `relative import "${spec}" resolves to a feature barrel`,
                )
                break
              }
              if (resolved.startsWith(fpath + '/')) {
                const featureRelative = relative(fpath, resolved)
                if (isRouteEntryImport(featureRelative)) break
                push(
                  'no-deep-feature-import-relative',
                  p,
                  `relative import "${spec}" reaches into feature ` +
                    `internals — import route entry files only`,
                )
                break
              }
            }
          }
        }
      }
    }
  }

  await walk(srcRoot)
}

function report() {
  const groupBy = (list) => {
    const byRule = new Map()
    for (const v of list) {
      if (!byRule.has(v.rule)) byRule.set(v.rule, [])
      byRule.get(v.rule).push(v)
    }
    return byRule
  }

  const errCount = violations.length
  const warnCount = warnings.length

  if (errCount === 0 && warnCount === 0) {
    console.log(
      `✓ Bulletproof React conformance: ` +
        `${featureCount} feature(s) checked, no violations.`,
    )
    return 0
  }

  console.log(
    `Bulletproof React conformance: ${featureCount} feature(s) checked.`,
  )
  console.log(`  ${errCount} violation(s), ${warnCount} warning(s).\n`)

  if (errCount > 0) {
    const byRule = groupBy(violations)
    console.log('Violations:')
    for (const [rule, items] of byRule) {
      console.log(`  [${rule}] (${items.length})`)
      for (const it of items) console.log(`    • ${it.file} — ${it.message}`)
    }
    console.log('')
  }

  if (warnCount > 0) {
    const byRule = groupBy(warnings)
    console.log('Warnings:')
    for (const [rule, items] of byRule) {
      console.log(`  [${rule}] (${items.length})`)
      for (const it of items) console.log(`    • ${it.file} — ${it.message}`)
    }
    console.log('')
  }

  console.log(
    'Reference: web-app/.cursor/rules/bulletproof-react-feature-structure.mdc',
  )
  return errCount > 0 ? 1 : 0
}

async function main() {
  const features = await findFeatures()
  featureCount = features.length

  for (const feature of features) {
    await checkFeatureShape(feature)
    await checkFileNaming(feature)
    await checkInternalImports(feature, features)
  }
  await checkExternalDeepImports(features)

  process.exit(report())
}

main().catch((err) => {
  console.error('check-bulletproof-react failed:', err)
  process.exit(2)
})
