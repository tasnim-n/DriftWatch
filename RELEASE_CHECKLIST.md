# DriftWatch Research Release Checklist

Release candidate: `0.2.0-research-rc1`

Source baseline: `23ac32fdde3afecd9318f8d485ea7875fbc8b41e`

## Verification

- [ ] Working tree clean — intentionally pending until Phase 8A outputs are reviewed and committed
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
- [ ] Architecture figure completed — figure plan is ready; rendering is pending
- [ ] Venue selected
- [ ] Venue formatting complete
- [ ] Release tag created
- [ ] Public archive created

## Release tag plan

- Proposed tag: `v0.2.0-research`
- Commit to tag: the future commit containing the reviewed Phase 8A outputs; its source baseline is `23ac32fdde3afecd9318f8d485ea7875fbc8b41e`.
- Do not tag the baseline commit because it does not contain this release metadata.
- Before tagging: review the diff, confirm the manifest checksum after checkout, rerun the public verifier and full suite, confirm a clean worktree, commit only approved Phase 8A paths, and verify the committed HEAD is synchronized with its intended remote.

## Archival plan

After the release commit is reviewed and tagged, generate the public archive from the Git object database, conceptually:

```powershell
git archive --format=zip --output DriftWatch-v0.2.0-research.zip v0.2.0-research
```

Verify the archive file list against `RELEASE_INVENTORY.md`, then publish an archive checksum separately. Do not zip the developer workspace: ignored raw review returns, rationale-bearing workspaces, local corpus archives, `.env`, `.venv`, caches, and temporary directories must remain outside the release.
