# DriftWatch Research Release Checklist

Release candidate: `0.2.0-research-rc1`

Source baseline: `e405295403f5f3c746c3954f88b1063f9d7eb169`

## Verification

- [ ] Working tree clean — intentionally pending until Phase 8B outputs are reviewed and committed
- [x] `origin/main` synchronized with the source baseline
- [x] Public human-validation verifier passes
- [x] Full test suite passes: 223 passed, 0 failed, 0 errors, 0 skipped
- [x] Public evidence hashes pass
- [x] Gold Set manifest hash passes
- [x] Paper evidence map passes
- [x] Paper submission is free of submission-blocking placeholders
- [x] References are clean: 22 verified, 0 gaps, 0 missing, 0 uncited, 0 fabricated
- [x] Private human-review material is excluded from the intended Git release surface
- [x] Release manifest generated
- [x] Release manifest checksum verified
- [x] Release notes ready
- [x] Architecture figure completed — SVG source, PNG fallback, caption, and public evidence map are ready
- [ ] Venue selected
- [ ] Venue formatting complete
- [ ] Release tag created
- [ ] Public archive created

## Release tag plan

- Proposed tag: `v0.2.0-research`
- Commit to tag: the future commit containing the reviewed Phase 8B publication outputs; its source baseline is `e405295403f5f3c746c3954f88b1063f9d7eb169`.
- Do not tag the baseline commit because it does not contain the final figure or manuscript proofread.
- Before tagging: review the diff, confirm the manifest checksum after checkout, rerun the public verifier and full suite, confirm a clean worktree, commit only approved Phase 8B paths, and verify the committed HEAD is synchronized with its intended remote.

## Archival plan

After the release commit is reviewed and tagged, generate the public archive from the Git object database, conceptually:

```powershell
git archive --format=zip --output DriftWatch-v0.2.0-research.zip v0.2.0-research
```

Verify the archive file list against `RELEASE_INVENTORY.md`, then publish an archive checksum separately. Do not zip the developer workspace: ignored raw review returns, rationale-bearing workspaces, local corpus archives, `.env`, `.venv`, caches, and temporary directories must remain outside the release.
