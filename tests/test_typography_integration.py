import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = ROOT / "youtube-video-typography-devpack"
SCRIPTS = ROOT / "scripts"
TYP_ROOT = PACK_ROOT / "scripts"
WORKFLOWS = ROOT / "workflows"
PS = which("pwsh") or which("powershell")


class TypographyIntegrationBaselineTests(unittest.TestCase):
    def test_typography_manifest_and_entrypoints(self):
        manifest_path = PACK_ROOT / "manifest.json"
        self.assertTrue(manifest_path.is_file(), manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest.get("name"), "youtube-video-typography-devpack")
        self.assertEqual(manifest.get("integrationMode"), "subproject")
        self.assertEqual(manifest.get("rootEntrypoint"), "../scripts/typography.ps1")
        self.assertTrue(manifest.get("safeByDefault"), manifest)

        root_typography = SCRIPTS / "typography.ps1"
        self.assertTrue(root_typography.is_file(), root_typography)
        self.assertTrue((TYP_ROOT / "typography_plan.py").is_file())
        self.assertTrue((TYP_ROOT / "generate_dynamic_ass.py").is_file())
        self.assertTrue((TYP_ROOT / "validate_typography_project.py").is_file())
        self.assertFalse((ROOT / "scripts" / "typography_core.py").exists())


    def test_typography_check_manifest_outputs(self):
        workflow = ROOT / "workflows" / "dynamic-typography.md"
        self.assertTrue(workflow.is_file(), "Missing workflow appendix: workflows/dynamic-typography.md")
        content = workflow.read_text(encoding="utf-8")
        self.assertIn("Visual Plan", content)

    def test_devpack_sha256_manifest(self):
        manifest_path = PACK_ROOT / "SHA256SUMS.txt"
        lines = [
            line.strip()
            for line in manifest_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertGreater(len(lines), 10)
        for line in lines:
            match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
            self.assertIsNotNone(match, line)
            expected, relative = match.groups()
            self.assertNotIn("..", Path(relative).parts)
            target = PACK_ROOT / Path(relative)
            self.assertTrue(target.is_file(), target)
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)

    def test_remotion_demo_routes_through_safe_wrapper(self):
        remotion_root = PACK_ROOT / "typography" / "remotion"
        package = json.loads(
            (remotion_root / "package.json").read_text(encoding="utf-8")
        )
        render_command = package["scripts"]["render:demo"]
        self.assertIn("scripts/render-demo.ps1", render_command)
        self.assertNotIn("remotion render", render_command)
        wrapper = (remotion_root / "scripts" / "render-demo.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("Output already exists", wrapper)
        self.assertIn("Output appeared during rendering", wrapper)
        self.assertIn("Staged output retained", wrapper)


class TypographyWrapperSmokeTests(unittest.TestCase):
    def setUp(self):
        if not PS:
            self.skipTest("PowerShell not available")
        if not (SCRIPTS / "check-typography-dependencies.ps1").is_file():
            self.skipTest("Typography wrapper missing")

    def run_pwsh(self, *arguments, input_text=None) -> subprocess.CompletedProcess:
        command = [
            PS,
            "-NoLogo",
            "-NoProfile",
            "-File",
            str(SCRIPTS / "typography.ps1"),
            *map(str, arguments),
        ]
        return subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            errors="replace",
            input=input_text,
            capture_output=True,
        )

    def test_wrapper_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="ytv_typography_") as temp:
            work = Path(temp)
            srt = work / "字幕.srt"
            plan = work / "plan.json"

            srt.write_text(
                """1\n00:00:00,000 --> 00:00:01,500\n字幕測試\n""",
                encoding="utf-8",
            )

            first = self.run_pwsh(
                "plan",
                "-InputPath",
                srt,
                "-OutputPath",
                plan,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertTrue(plan.is_file())

            second = self.run_pwsh(
                "plan",
                "-InputPath",
                srt,
                "-OutputPath",
                plan,
            )
            self.assertNotEqual(second.returncode, 0, second.stdout + second.stderr)

    @unittest.skipUnless(which("ffmpeg") and which("ffprobe"), "FFmpeg/FFprobe are required")
    def test_full_mvp_path_smoke(self):
        with tempfile.TemporaryDirectory(prefix="ytv_typography_smoke_") as temp:
            work = Path(temp)
            source = work / "source.mp4"
            srt = work / "字幕 測試.srt"
            plan = work / "output.plan.json"
            ass = work / "output.typography.ass"
            report = work / "output.typography.qa.json"
            output = work / "out_typography 測試.mp4"

            make_video = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=320x240:rate=24:duration=5",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=48000:duration=5",
                "-shortest",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(source),
            ]
            generated = subprocess.run(
                make_video,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)

            srt.write_text(
                """1\n00:00:00,000 --> 00:00:01,200\n第一則測試字幕\n\n2\n00:00:01,300 --> 00:00:02,500\n第二則字幕\n""",
                encoding="utf-8",
            )

            plan_result = self.run_pwsh(
                "plan",
                "-InputPath",
                srt,
                "-OutputPath",
                plan,
            )
            self.assertEqual(plan_result.returncode, 0, plan_result.stdout + plan_result.stderr)

            ass_result = self.run_pwsh(
                "ass",
                "-InputPath",
                plan,
                "-OutputPath",
                ass,
            )
            self.assertEqual(ass_result.returncode, 0, ass_result.stdout + ass_result.stderr)
            self.assertTrue(ass.is_file())

            validate_result = self.run_pwsh(
                "validate",
                "-InputPath",
                plan,
                "-OutputPath",
                report,
            )
            self.assertEqual(validate_result.returncode, 0, validate_result.stdout + validate_result.stderr)
            self.assertTrue(report.is_file())
            self.assertIn("eventCount", report.read_text(encoding="utf-8"))

            render_result = self.run_pwsh(
                "render",
                "-InputPath",
                source,
                "-PlanPath",
                plan,
                "-AssPath",
                ass,
                "-OutputPath",
                output,
            )
            self.assertEqual(render_result.returncode, 0, render_result.stdout + render_result.stderr)
            self.assertTrue(output.is_file())
            original_output = output.read_bytes()
            original_ass = ass.read_bytes()

            ffprobe = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,size",
                "-of",
                "json",
                str(output),
            ]
            probe = subprocess.run(
                ffprobe,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(probe.returncode, 0, probe.stderr)
            metadata = json.loads(probe.stdout)
            self.assertIn("format", metadata)
            self.assertGreater(int(metadata["format"]["size"]), 0)

            forced_render = self.run_pwsh(
                "render",
                "-InputPath",
                source,
                "-PlanPath",
                plan,
                "-AssPath",
                ass,
                "-OutputPath",
                output,
                "-Force",
            )
            self.assertEqual(
                forced_render.returncode,
                0,
                forced_render.stdout + forced_render.stderr,
            )
            output_backups = list(work.glob(f"{output.name}.backup-*"))
            self.assertEqual(len(output_backups), 1)
            self.assertEqual(output_backups[0].read_bytes(), original_output)
            self.assertEqual(ass.read_bytes(), original_ass)
            self.assertEqual(list(work.glob(f"{ass.name}.backup-*")), [])

            default_output = work / "automatic.typography.mp4"
            default_render = self.run_pwsh(
                "render",
                "-InputPath",
                source,
                "-PlanPath",
                plan,
                "-OutputPath",
                default_output,
            )
            self.assertEqual(
                default_render.returncode,
                0,
                default_render.stdout + default_render.stderr,
            )
            self.assertTrue((work / "automatic.typography.ass").is_file())
            self.assertFalse((work / "automatic.typography.typography.ass").exists())
