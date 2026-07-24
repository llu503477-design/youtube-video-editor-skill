import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from typography_core import (  # noqa: E402
    apply_effect_budget,
    build_visual_plan,
    classify_text,
    escape_ass_text,
    parse_srt_text,
    seconds_to_ass,
    write_json_safely,
)
from generate_dynamic_ass import generate_ass  # noqa: E402
from validate_typography_project import validate_plan  # noqa: E402


class SrtParsingTests(unittest.TestCase):
    def test_parse_multiline_and_milliseconds(self):
        cues = parse_srt_text(
            """1
00:00:01,250 --> 00:00:03,500
第一行
第二行
"""
        )
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].start, 1.25)
        self.assertEqual(cues[0].end, 3.5)
        self.assertEqual(cues[0].text, "第一行\n第二行")

    def test_rejects_invalid_timestamp(self):
        with self.assertRaises(ValueError):
            parse_srt_text(
                """1
00:88:00,000 --> 00:00:02,000
錯誤
"""
            )

    def test_ass_time_rollover(self):
        self.assertEqual(seconds_to_ass(59.999), "0:01:00.00")


class SemanticTests(unittest.TestCase):
    def test_warning(self):
        result = classify_text("千萬不要這樣做")
        self.assertEqual(result["templateId"], "warning-alert")
        self.assertTrue(result["strongEffect"])

    def test_number(self):
        result = classify_text("只要三分鐘")  # Chinese numeral is not regex number.
        self.assertEqual(result["templateId"], "clean-bottom")
        result = classify_text("只要 3 分鐘")
        self.assertEqual(result["templateId"], "big-number")

    def test_punchline(self):
        result = classify_text("這個真的太誇張了！")
        self.assertEqual(result["templateId"], "impact-slam")

    def test_budget_downgrades_lower_priority(self):
        events = [
            {
                "start": 1.0,
                "intensity": 0.9,
                "strongEffect": True,
                "templateId": "impact-slam",
                "purpose": "punchline",
            },
            {
                "start": 5.0,
                "intensity": 0.8,
                "strongEffect": True,
                "templateId": "warning-alert",
                "purpose": "warning",
            },
        ]
        apply_effect_budget(events)
        self.assertTrue(events[0]["strongEffect"])
        self.assertFalse(events[1]["strongEffect"])
        self.assertEqual(events[1]["templateId"], "clean-bottom")

    def test_budget_uses_sliding_windows_across_ten_second_boundary(self):
        events = [
            {
                "start": 9.9,
                "intensity": 0.8,
                "strongEffect": True,
                "templateId": "impact-slam",
                "purpose": "punchline",
            },
            {
                "start": 10.0,
                "intensity": 0.9,
                "strongEffect": True,
                "templateId": "warning-alert",
                "purpose": "warning",
            },
        ]
        apply_effect_budget(events)
        self.assertFalse(events[0]["strongEffect"])
        self.assertTrue(events[1]["strongEffect"])


class AssTests(unittest.TestCase):
    def test_escape_override_blocks_and_multiline(self):
        escaped = escape_ass_text("{danger}\nnext")
        self.assertNotIn("{danger}", escaped)
        self.assertIn("｛danger｝", escaped)
        self.assertIn(r"\N", escaped)

    def test_generate_ass_has_styles_and_events(self):
        cues = parse_srt_text(
            """1
00:00:00,000 --> 00:00:01,500
這個真的太誇張了！

2
00:00:02,000 --> 00:00:03,000
只要 3 分鐘
"""
        )
        plan = build_visual_plan(cues)
        output = generate_ass(plan)
        self.assertIn("[V4+ Styles]", output)
        self.assertIn("Style: Impact", output)
        self.assertIn("Style: Number", output)
        self.assertEqual(output.count("Dialogue:"), 2)


class ValidationTests(unittest.TestCase):
    def test_valid_plan(self):
        cues = parse_srt_text(
            """1
00:00:00,000 --> 00:00:01,000
正常字幕
"""
        )
        report = validate_plan(build_visual_plan(cues))
        self.assertTrue(report["valid"], report["errors"])

    def test_reject_unknown_template(self):
        cues = parse_srt_text(
            """1
00:00:00,000 --> 00:00:01,000
正常字幕
"""
        )
        plan = build_visual_plan(cues)
        plan["events"][0]["templateId"] = "unknown"
        report = validate_plan(plan)
        self.assertFalse(report["valid"])

    def test_rejects_missing_schema_required_event_fields(self):
        cues = parse_srt_text(
            """1
00:00:00,000 --> 00:00:01,000
正常字幕
"""
        )
        plan = build_visual_plan(cues)
        for field in (
            "purpose",
            "emotion",
            "keywords",
            "strongEffect",
            "readingPriority",
        ):
            broken = json.loads(json.dumps(plan))
            del broken["events"][0][field]
            report = validate_plan(broken)
            self.assertFalse(report["valid"], field)

    def test_rejects_non_object_nan_short_multiline_and_sliding_budget(self):
        self.assertFalse(validate_plan([])["valid"])
        invalid_event_plan = {
            "schemaVersion": "1.0",
            "project": {
                "width": 1080,
                "height": 1920,
                "fps": 30,
                "duration": 1,
                "language": "zh-TW",
            },
            "events": ["not-an-object"],
        }
        self.assertFalse(validate_plan(invalid_event_plan)["valid"])

        cues = parse_srt_text(
            """1
00:00:09,900 --> 00:00:10,900
第一則

2
00:00:10,000 --> 00:00:11,000
第二則
"""
        )
        plan = build_visual_plan(cues)
        plan["project"]["fps"] = float("nan")
        plan["events"][0]["strongEffect"] = True
        plan["events"][1]["strongEffect"] = True
        plan["events"][0]["text"] = "一\n二\n三"
        plan["events"][0]["end"] = 10.2
        report = validate_plan(plan)
        self.assertFalse(report["valid"])
        joined = "\n".join(report["errors"])
        self.assertIn("project.fps", joined)
        self.assertIn("at least 0.650s", "\n".join(report["warnings"]))
        self.assertIn("at most 2 lines", joined)
        self.assertIn("effect budget exceeded", joined)

    def test_long_legal_srt_cue_remains_renderable_with_warning(self):
        plan = build_visual_plan(
            parse_srt_text(
                """1
00:00:00,000 --> 00:00:04,000
合法的長字幕
"""
            )
        )
        report = validate_plan(plan)
        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(
            any("at most 3.200s" in warning for warning in report["warnings"])
        )

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "plan.json"
            write_json_safely(target, {"a": 1})
            with self.assertRaises(FileExistsError):
                write_json_safely(target, {"a": 2})
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"a": 1})

    def test_no_force_atomic_publish_rejects_racing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "plan.json"
            with patch("typography_core.os.link", side_effect=FileExistsError):
                with self.assertRaises(FileExistsError):
                    write_json_safely(target, {"a": 1})
            self.assertFalse(target.exists())

    def test_cli_refuses_input_output_aliases(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            srt = work / "captions.srt"
            srt.write_text(
                "1\n00:00:00,000 --> 00:00:01,000\n字幕\n",
                encoding="utf-8",
            )
            original_srt = srt.read_bytes()
            plan_alias = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "typography_plan.py"),
                    str(srt),
                    str(srt),
                    "--force",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(plan_alias.returncode, 0)
            self.assertEqual(srt.read_bytes(), original_srt)

            plan = work / "plan.json"
            plan.write_text(
                json.dumps(
                    build_visual_plan(
                        parse_srt_text(
                            "1\n00:00:00,000 --> 00:00:01,000\n字幕\n"
                        )
                    ),
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            original_plan = plan.read_bytes()
            for script, arguments in (
                ("generate_dynamic_ass.py", [str(plan), str(plan), "--force"]),
                (
                    "validate_typography_project.py",
                    [str(plan), "--report", str(plan), "--force"],
                ),
            ):
                result = subprocess.run(
                    [sys.executable, str(SCRIPTS / script), *arguments],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertNotEqual(result.returncode, 0, script)
                self.assertEqual(plan.read_bytes(), original_plan, script)


if __name__ == "__main__":
    unittest.main()
