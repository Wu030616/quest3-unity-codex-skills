# Quest 3 Unity Codex Skills

Portable Agent Skills for designing and verifying Unity XR/MR interfaces targeting Meta Quest 3. The repository follows the open Agent Skills folder format and is intended for Codex and other compatible agents.

This is an unofficial community project. It is not affiliated with, sponsored by, or endorsed by Meta Platforms or Unity Technologies.

[简体中文](README.zh-CN.md)

## Included skills

| Skill | Purpose |
| --- | --- |
| `quest3-verify-first` | Verifies unstable Quest, Unity, OpenXR, package, permission, and device claims against live primary sources and the actual project before mutation. |
| `unity-xr-mr-ui-director` | Designs, implements, audits, and validates spatial Unity UI with measurable geometry, explicit interaction ownership, MR placement rules, and Quest 3 device gates. |

Install both skills. The UI director routes current platform and package claims through `quest3-verify-first`.

## Safety boundary

The repository contains instructions, references, and a read-only Python project auditor. It does not bundle Unity packages, Meta SDK binaries, `metavr`, telemetry hooks, ADB tooling, 3D assets, or a Unity Editor MCP bridge.

The skills do not authorize device or project mutations by themselves. Package changes, APK installation, application launch, device capture, and similar actions still require the current user request and an actually configured tool.

## Installation

Clone the repository:

```bash
git clone https://github.com/Wu030616/quest3-unity-codex-skills.git
cd quest3-unity-codex-skills
```

For a Codex user-level installation on macOS or Linux, create the skill directory and link both folders:

```bash
mkdir -p "$HOME/.agents/skills"
ln -s "$PWD/skills/quest3-verify-first" "$HOME/.agents/skills/quest3-verify-first"
ln -s "$PWD/skills/unity-xr-mr-ui-director" "$HOME/.agents/skills/unity-xr-mr-ui-director"
```

Stop if either destination already exists. Inspect the existing installation instead of overwriting it. Other Agent Skills clients may use a different user- or project-level directory; follow that client's documentation.

## Example prompts

```text
Use $quest3-verify-first to verify this Unity project's current Quest 3,
OpenXR, and package requirements before proposing changes.
```

```text
Use $unity-xr-mr-ui-director to design a room-locked mixed-reality menu
for Quest 3, then define the physical dimensions and on-device QA gates.
```

## Read-only Unity audit

The UI skill includes a standard-library Python auditor:

```bash
python3 skills/unity-xr-mr-ui-director/scripts/audit_unity_xr_ui.py \
  /absolute/path/to/unity-project
```

If Unity Hub uses a custom editor directory, pass it explicitly. Repeat the option for multiple roots:

```bash
python3 skills/unity-xr-mr-ui-director/scripts/audit_unity_xr_ui.py \
  /absolute/path/to/unity-project \
  --unity-editors-path /absolute/path/to/Unity/Hub/Editor
```

Alternatively, set `UNITY_HUB_EDITORS_PATH` to one or more roots separated by the operating system's path separator. Resolution order is command-line paths, then the environment variable, then platform defaults.

The audit emits JSON. Confirmed problems appear in `warnings` and control the exit code. Ambiguous static findings appear in `observations` and do not fail the audit. The script does not open Unity or modify the project. Serialized component detection remains a static check; the final UI gate still requires compilation, interaction testing, and judgement inside a Quest 3 headset.

## Development

Run the repository checks with Python 3.10 or later:

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -v
```

The CI workflow runs the same checks on Linux, macOS, and Windows without downloading Unity.

## Version and provenance

The initial public package version is `0.1.0`. Source provenance and modification notices live inside each skill's `SOURCE.md`. Third-party boundaries are recorded in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

Meta, Meta Quest, Horizon, Unity, and related names and marks belong to their respective owners. Their use here identifies interoperability targets and source material.
