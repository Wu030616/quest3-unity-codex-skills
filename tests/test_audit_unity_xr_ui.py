from __future__ import annotations

from contextlib import ExitStack, redirect_stdout
import hashlib
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock


sys.dont_write_bytecode = True
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPOSITORY_ROOT
    / "skills"
    / "unity-xr-mr-ui-director"
    / "scripts"
    / "audit_unity_xr_ui.py"
)
SPEC = importlib.util.spec_from_file_location("audit_unity_xr_ui", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


VERSION = "6000.0.77f1"
EVENT_SYSTEM_GUID = "11111111111111111111111111111111"
STANDALONE_GUID = "22222222222222222222222222222222"
INPUT_SYSTEM_GUID = "33333333333333333333333333333333"
XR_UI_GUID = "44444444444444444444444444444444"
RAYCASTER_GUID = "55555555555555555555555555555555"
META_POINTABLE_CANVAS_GUID = "66666666666666666666666666666666"
META_POINTABLE_MODULE_GUID = "77777777777777777777777777777777"

CORE_DEPENDENCIES = {
    "com.unity.inputsystem": "1.19.0",
    "com.unity.xr.management": "4.5.4",
    "com.unity.xr.openxr": "1.16.1",
    "com.unity.xr.interaction.toolkit": "3.0.11",
    "com.unity.ugui": "2.0.0",
}


def make_project(
    base: Path,
    *,
    dependencies: dict[str, str] | None = None,
    create_assets: bool = True,
) -> Path:
    project = base / "UnityProject"
    (project / "ProjectSettings").mkdir(parents=True)
    (project / "Packages").mkdir(parents=True)
    if create_assets:
        (project / "Assets").mkdir(parents=True)
    (project / "ProjectSettings" / "ProjectVersion.txt").write_text(
        f"m_EditorVersion: {VERSION}\n",
        encoding="utf-8",
    )
    (project / "Packages" / "manifest.json").write_text(
        json.dumps({"dependencies": dependencies if dependencies is not None else CORE_DEPENDENCIES}),
        encoding="utf-8",
    )
    return project


def add_component_meta(project: Path, filename: str, guid: str) -> Path:
    path = project / "Library" / "PackageCache" / "test.package@hash" / "Runtime" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"fileFormatVersion: 2\nguid: {guid}\n", encoding="utf-8")
    return path


def write_serialized_asset(
    project: Path,
    filename: str,
    *,
    component_guids: list[str] | None = None,
    canvas_count: int = 0,
) -> Path:
    path = project / "Assets" / "Scenes" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    blocks: list[str] = []
    next_file_id = 1
    for _ in range(canvas_count):
        blocks.append(
            f"--- !u!223 &{next_file_id}\n"
            "Canvas:\n"
            "  m_ObjectHideFlags: 0\n"
        )
        next_file_id += 1
    for guid in component_guids or []:
        blocks.append(
            f"--- !u!114 &{next_file_id}\n"
            "MonoBehaviour:\n"
            "  m_GameObject: {fileID: 100}\n"
            f"  m_Script: {{fileID: 11500000, guid: {guid}, type: 3}}\n"
        )
        next_file_id += 1
    path.write_text("".join(blocks), encoding="utf-8")
    return path


def make_editor_root(base: Path, platform: str, version: str = VERSION, *, legacy_linux: bool = False) -> Path:
    root = base / f"editors-{platform}"
    version_dir = root / version
    candidates = AUDIT.unity_editor_executable_candidates(version_dir, platform)
    executable = candidates[1] if legacy_linux else candidates[0]
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_text("", encoding="utf-8")
    return root


def run_main(*arguments: object) -> tuple[int, dict[str, object]]:
    output = StringIO()
    argv = [str(SCRIPT_PATH), *(str(argument) for argument in arguments)]
    with mock.patch.object(sys, "argv", argv), redirect_stdout(output):
        return_code = AUDIT.main()
    return return_code, json.loads(output.getvalue())


def project_snapshot(project: Path) -> dict[str, tuple[bool, int, int, int, str | None]]:
    snapshot: dict[str, tuple[bool, int, int, int, str | None]] = {}
    for path in [project, *sorted(project.rglob("*"))]:
        info = path.stat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        relative = "." if path == project else str(path.relative_to(project))
        snapshot[relative] = (
            path.is_dir(),
            info.st_size,
            info.st_mtime_ns,
            stat.S_IMODE(info.st_mode),
            digest,
        )
    return snapshot


class EditorDiscoveryTests(unittest.TestCase):
    def test_discovers_all_supported_editor_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for platform in ("darwin", "win32", "linux"):
                with self.subTest(platform=platform):
                    root = make_editor_root(base, platform)
                    self.assertEqual(AUDIT.installed_unity_versions([root], platform), [VERSION])

    def test_discovers_legacy_linux_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_editor_root(Path(directory), "linux", legacy_linux=True)
            self.assertEqual(AUDIT.installed_unity_versions([root], "linux"), [VERSION])

    def test_ignores_version_directory_without_editor_executable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "Editors"
            (root / VERSION).mkdir(parents=True)
            self.assertEqual(AUDIT.installed_unity_versions([root], "darwin"), [])

    def test_environment_override_supports_multiple_deduplicated_roots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first = base / "first"
            second = base / "second"
            environment = {
                AUDIT.UNITY_HUB_EDITORS_ENV: os.pathsep.join(
                    (str(first), str(second), str(first))
                )
            }
            roots = AUDIT.default_unity_editor_roots(platform="linux", environ=environment, home=base)
            self.assertEqual(roots, [first, second])

    def test_cli_editor_root_overrides_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project = make_project(base)
            cli_root = make_editor_root(base, sys.platform)
            environment_root = base / "environment-editors"
            with mock.patch.dict(
                os.environ,
                {AUDIT.UNITY_HUB_EDITORS_ENV: str(environment_root)},
                clear=False,
            ):
                return_code, result = run_main(
                    project,
                    "--unity-editors-path",
                    cli_root,
                )
            self.assertEqual(return_code, 0)
            self.assertEqual(result["installed_editors"], [VERSION])
            self.assertEqual(result["editor_search_roots"], [str(cli_root.resolve())])


class ProjectAndManifestTests(unittest.TestCase):
    def test_missing_project_returns_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            return_code, result = run_main(missing)
            self.assertEqual(return_code, 2)
            self.assertEqual(result["error_code"], "project_not_found")
            self.assertTrue(result["read_only"])

    def test_non_unity_directory_returns_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            return_code, result = run_main(directory)
            self.assertEqual(return_code, 2)
            self.assertEqual(result["error_code"], "not_unity_project")

    def test_missing_manifest_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = make_project(Path(directory))
            (project / "Packages" / "manifest.json").unlink()
            with self.assertRaisesRegex(ValueError, "required JSON file not found"):
                AUDIT.package_report(project)

    def test_malformed_manifest_shapes_are_errors(self) -> None:
        cases = (
            ("{", "cannot parse"),
            ("[]", "expected a JSON object"),
            ('{"dependencies": []}', "expected a dependencies object"),
        )
        with tempfile.TemporaryDirectory() as directory:
            project = make_project(Path(directory))
            manifest = project / "Packages" / "manifest.json"
            for content, expected in cases:
                with self.subTest(content=content):
                    manifest.write_text(content, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, expected):
                        AUDIT.package_report(project)

    def test_missing_core_package_produces_only_its_group_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dependencies = dict(CORE_DEPENDENCIES)
            dependencies.pop("com.unity.xr.openxr")
            project = make_project(Path(directory), dependencies=dependencies)
            packages, _ = AUDIT.package_report(project)
            scan = AUDIT.scan_assets(project, 100, 1024 * 1024)
            warnings = AUDIT.warnings_for(VERSION, [VERSION], packages, scan)
            package_warnings = [warning for warning in warnings if "core package group missing" in warning]
            self.assertEqual(package_warnings, ["core package group missing: openxr"])

    def test_missing_assets_keeps_stable_scan_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = make_project(Path(directory), create_assets=False)
            scan = AUDIT.scan_assets(project, 17, 1024)
            self.assertEqual(scan["scan_limit"], 17)
            self.assertEqual(scan["scanned_files"], 0)
            self.assertEqual(scan["asset_component_counts"], {})
            self.assertIn("component_detection", scan)

    def test_invalid_scan_limits_return_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = make_project(Path(directory))
            return_code, result = run_main(project, "--max-files", 0)
            self.assertEqual(return_code, 2)
            self.assertEqual(result["error_code"], "invalid_scan_limits")


class ComponentGuidTests(unittest.TestCase):
    def warnings(self, project: Path) -> tuple[dict[str, object], list[str]]:
        packages, _ = AUDIT.package_report(project)
        scan = AUDIT.scan_assets(project, 100, 1024 * 1024)
        return scan, AUDIT.warnings_for(VERSION, [VERSION], packages, scan)

    def test_guid_detection_recognizes_valid_xr_ui_scene(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = make_project(Path(directory))
            add_component_meta(project, "EventSystem.cs.meta", EVENT_SYSTEM_GUID)
            add_component_meta(project, "XRUIInputModule.cs.meta", XR_UI_GUID)
            add_component_meta(project, "TrackedDeviceGraphicRaycaster.cs.meta", RAYCASTER_GUID)
            write_serialized_asset(
                project,
                "Valid.unity",
                component_guids=[EVENT_SYSTEM_GUID, XR_UI_GUID, RAYCASTER_GUID],
                canvas_count=1,
            )

            scan, warnings = self.warnings(project)
            counts = scan["asset_component_counts"]["Assets/Scenes/Valid.unity"]
            self.assertEqual(counts["event_system"], 1)
            self.assertEqual(counts["xr_ui_input_module"], 1)
            self.assertEqual(counts["tracked_device_graphic_raycaster"], 1)
            self.assertFalse(any("TrackedDeviceGraphicRaycaster" in warning for warning in warnings))
            self.assertFalse(any("multiple UI input" in warning for warning in warnings))

    def test_two_module_families_in_one_asset_warn(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = make_project(Path(directory))
            add_component_meta(project, "XRUIInputModule.cs.meta", XR_UI_GUID)
            add_component_meta(project, "InputSystemUIInputModule.cs.meta", INPUT_SYSTEM_GUID)
            write_serialized_asset(
                project,
                "Conflict.unity",
                component_guids=[XR_UI_GUID, INPUT_SYSTEM_GUID],
            )
            _, warnings = self.warnings(project)
            self.assertTrue(any("multiple UI input modules" in warning for warning in warnings))

    def test_duplicate_same_module_in_one_asset_warns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = make_project(Path(directory))
            add_component_meta(project, "XRUIInputModule.cs.meta", XR_UI_GUID)
            write_serialized_asset(
                project,
                "Duplicate.unity",
                component_guids=[XR_UI_GUID, XR_UI_GUID],
            )
            _, warnings = self.warnings(project)
            self.assertTrue(any("xr_ui_input_module=2" in warning for warning in warnings))

    def test_module_families_in_separate_assets_do_not_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = make_project(Path(directory))
            add_component_meta(project, "XRUIInputModule.cs.meta", XR_UI_GUID)
            add_component_meta(project, "StandaloneInputModule.cs.meta", STANDALONE_GUID)
            write_serialized_asset(project, "XR.unity", component_guids=[XR_UI_GUID])
            write_serialized_asset(project, "Desktop.unity", component_guids=[STANDALONE_GUID])
            _, warnings = self.warnings(project)
            self.assertFalse(any("multiple UI input modules" in warning for warning in warnings))

    def test_meta_canvas_and_module_are_not_duplicate_input_modules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = make_project(Path(directory))
            add_component_meta(project, "PointableCanvas.cs.meta", META_POINTABLE_CANVAS_GUID)
            add_component_meta(
                project,
                "PointableCanvasModule.cs.meta",
                META_POINTABLE_MODULE_GUID,
            )
            write_serialized_asset(
                project,
                "MetaUI.unity",
                component_guids=[META_POINTABLE_CANVAS_GUID, META_POINTABLE_MODULE_GUID],
            )
            scan, warnings = self.warnings(project)
            counts = scan["asset_component_counts"]["Assets/Scenes/MetaUI.unity"]
            self.assertEqual(counts["meta_pointable_canvas"], 1)
            self.assertEqual(counts["meta_pointable_canvas_module"], 1)
            self.assertFalse(any("multiple UI input modules" in warning for warning in warnings))

    def test_duplicate_event_system_in_one_asset_warns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = make_project(Path(directory))
            add_component_meta(project, "EventSystem.cs.meta", EVENT_SYSTEM_GUID)
            write_serialized_asset(
                project,
                "Events.unity",
                component_guids=[EVENT_SYSTEM_GUID, EVENT_SYSTEM_GUID],
            )
            _, warnings = self.warnings(project)
            self.assertTrue(any("multiple EventSystem components" in warning for warning in warnings))

    def test_unresolved_raycaster_is_unknown_not_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = make_project(Path(directory))
            write_serialized_asset(project, "Unknown.unity", canvas_count=1)
            scan, warnings = self.warnings(project)
            self.assertIn(
                "tracked_device_graphic_raycaster",
                scan["component_detection"]["unresolved"],
            )
            self.assertFalse(any("TrackedDeviceGraphicRaycaster" in warning for warning in warnings))

    def test_resolved_but_missing_raycaster_is_a_non_failing_observation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = make_project(Path(directory))
            add_component_meta(project, "TrackedDeviceGraphicRaycaster.cs.meta", RAYCASTER_GUID)
            write_serialized_asset(project, "MissingRaycaster.unity", canvas_count=1)
            scan, warnings = self.warnings(project)
            packages, _ = AUDIT.package_report(project)
            observations = AUDIT.observations_for(packages, scan)
            self.assertFalse(any("TrackedDeviceGraphicRaycaster" in warning for warning in warnings))
            self.assertTrue(
                any(
                    "Assets/Scenes/MissingRaycaster.unity without a TrackedDeviceGraphicRaycaster"
                    in observation
                    for observation in observations
                )
            )


class ReadOnlyGuaranteeTests(unittest.TestCase):
    def make_clean_fixture(self, base: Path) -> tuple[Path, Path]:
        project = make_project(base)
        editor_root = make_editor_root(base, sys.platform)
        add_component_meta(project, "EventSystem.cs.meta", EVENT_SYSTEM_GUID)
        add_component_meta(project, "XRUIInputModule.cs.meta", XR_UI_GUID)
        add_component_meta(project, "TrackedDeviceGraphicRaycaster.cs.meta", RAYCASTER_GUID)
        write_serialized_asset(
            project,
            "Clean.unity",
            component_guids=[EVENT_SYSTEM_GUID, XR_UI_GUID, RAYCASTER_GUID],
            canvas_count=1,
        )
        return project, editor_root

    def test_main_does_not_change_project_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project, editor_root = self.make_clean_fixture(Path(directory))
            before = project_snapshot(project)
            return_code, result = run_main(
                project,
                "--unity-editors-path",
                editor_root,
            )
            after = project_snapshot(project)
            self.assertEqual(return_code, 0, result)
            self.assertEqual(before, after)
            self.assertTrue(result["read_only"])

    def test_main_never_calls_common_path_mutators(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project, editor_root = self.make_clean_fixture(Path(directory))
            mutators = (
                "write_text",
                "write_bytes",
                "mkdir",
                "touch",
                "unlink",
                "rename",
                "replace",
                "rmdir",
                "chmod",
            )
            with ExitStack() as stack:
                for method_name in mutators:
                    stack.enter_context(
                        mock.patch.object(
                            Path,
                            method_name,
                            side_effect=AssertionError(f"unexpected Path.{method_name} call"),
                        )
                    )
                return_code, result = run_main(
                    project,
                    "--unity-editors-path",
                    editor_root,
                )
            self.assertEqual(return_code, 0, result)


if __name__ == "__main__":
    unittest.main()
