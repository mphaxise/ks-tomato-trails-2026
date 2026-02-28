# Release Snapshots

This folder stores versioned snapshots of tracker pages and source data used for each release.

## Layout

- `manifest.json`: ordered list of known versions and metadata.
- `RELEASE_NOTES.md`: human-readable release notes using `v<major>.<minor>-YYYY-MM-DD` sections.
- `<version-id>/metadata.json`: per-version metadata (source ref/commit, copied/missing files, notes).
- `<version-id>/data/...`: snapshot of intake/processed files.
- `<version-id>/tracker/...`: snapshot of generated HTML pages.

## Create Snapshot

```bash
python3 scripts/create_version_snapshot.py \
  --version-id v1.2-2026-02-28 \
  --source-ref WORKTREE \
  --release-date 2026-02-28 \
  --notes "Tomato-only workflow release"
```

## Create Git Tag

After merge to `master`, create an annotated tag using the same version id:

```bash
git checkout master
git pull origin master
git tag -a v1.2-2026-02-28 -m "Release v1.2-2026-02-28"
git push origin v1.2-2026-02-28
```

## Merge Guard

Before merge to `master`, run:

```bash
python3 scripts/verify_release_snapshot_guard.py --base-ref origin/master --head-ref HEAD --include-working-tree
```

The guard requires release-sensitive changes to include:
- `releases/manifest.json`
- `releases/v*/metadata.json`
- `releases/RELEASE_NOTES.md`

## Browse

- Local: `tracker/version-archive.html`
- Live (after deploy): `/version-archive`
