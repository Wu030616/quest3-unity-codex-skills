# Contributing

Keep changes narrow, reviewable, and verifiable.

## Before a pull request

1. Preserve each skill's safety boundary. Do not add implicit downloads, telemetry, package installation, device mutation, or broad shell access.
2. Verify unstable Quest, Unity, Android, OpenXR, package, permission, and store claims against live primary sources. Link the exact supporting page.
3. Do not vendor code, documentation, models, textures, fonts, or sample assets without a file-level license review and an update to `THIRD_PARTY_NOTICES.md`.
4. Keep `SKILL.md` below 500 lines. Put detailed material in directly linked `references/` files.
5. Add or update standard-library tests for script changes.

Run:

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -v
```

Report what was tested. Do not claim Quest 3 readability, comfort, interaction quality, or performance from an editor or simulator-only run.
