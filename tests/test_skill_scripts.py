import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ass = load_module("generate_bilingual_ass", "generate_bilingual_ass.py")
narrate = load_module("narrate", "narrate.py")
merge_srt = load_module("merge_bilingual_srt", "merge_bilingual_srt.py")
thumbnail = load_module("thumbnail", "thumbnail.py")


class SubtitleTests(unittest.TestCase):
    def test_ass_output_escapes_override_blocks_and_multiline_text(self):
        output = ass.generate_ass(
            [("00:00:01,000 --> 00:00:02,000", "<i>中文</i>\n{danger}")],
            [("00:00:01,000 --> 00:00:02,000", "English")],
        )

        self.assertIn(r"中文\N｛danger｝\N{\rEN}English", output)
        self.assertNotIn("{danger}", output)

    def test_invalid_timestamp_is_rejected(self):
        with self.assertRaises(ValueError):
            ass.srt_time_to_ass("not-a-timestamp")

    def test_timestamp_precision_rollover_and_time_based_alignment(self):
        self.assertEqual(ass.srt_time_to_ass("00:00:00,4"), "0:00:00.40")
        self.assertEqual(ass.srt_time_to_ass("00:00:59,999"), "0:01:00.00")

        output = ass.generate_ass(
            [
                ("00:00:00,000 --> 00:00:02,000", "中文一"),
                ("00:00:02,000 --> 00:00:04,000", "中文二"),
            ],
            [
                ("00:00:02,100 --> 00:00:03,900", "English two"),
                ("00:00:00,100 --> 00:00:01,900", "English one"),
            ],
            video_height=720,
        )
        dialogue = [line for line in output.splitlines() if line.startswith("Dialogue:")]
        self.assertIn("English one", dialogue[0])
        self.assertIn("English two", dialogue[1])
        self.assertIn("PlayResY: 720", output)

        merged = merge_srt.merge_bilingual(
            [
                ("1", "00:00:00,000 --> 00:00:02,000", "中文一"),
                ("2", "00:00:02,000 --> 00:00:04,000", "中文二"),
            ],
            [
                ("1", "00:00:02,100 --> 00:00:03,900", "English two"),
                ("2", "00:00:00,100 --> 00:00:01,900", "English one"),
            ],
        )
        self.assertIn("English one", merged[0])
        self.assertIn("English two", merged[1])

        spanning = ass.generate_ass(
            [
                ("00:00:00,000 --> 00:00:05,000", "前半"),
                ("00:00:05,000 --> 00:00:10,000", "後半"),
            ],
            [("00:00:00,000 --> 00:00:10,000", "One long English segment")],
        )
        spanning_dialogue = [
            line for line in spanning.splitlines() if line.startswith("Dialogue:")
        ]
        self.assertIn("One long English segment", spanning_dialogue[0])
        self.assertIn("One long English segment", spanning_dialogue[1])

        edge_groups, edge_unmatched = ass.align_english_to_chinese(
            [
                ("00:00:00,000 --> 00:00:05,000", "第一段"),
                ("00:00:05,000 --> 00:00:10,000", "第二段"),
            ],
            [("00:00:00,000 --> 00:00:05,001", "Boundary drift")],
        )
        self.assertEqual([len(group) for group in edge_groups], [1, 0])
        self.assertEqual(edge_unmatched, [])


class NarrationTimingTests(unittest.TestCase):
    def test_segment_delays_are_relative_not_cumulative_absolute_offsets(self):
        entries = narrate.generate_narration_srt(
            [
                (0, 1000, 500, "first"),
                (2000, 500, 400, "second"),
            ]
        )

        self.assertEqual(
            entries,
            [
                (1000, 1500, "first"),
                (2000, 2400, "second"),
            ],
        )

    def test_main_fails_closed_when_tts_fails(self):
        with tempfile.TemporaryDirectory(prefix="narrate_failure_") as temp:
            temp_path = Path(temp)
            script = temp_path / "script.txt"
            output = temp_path / "narration.wav"
            script.write_text("This segment should fail.\n", encoding="utf-8")
            argv = [
                "narrate.py",
                "--script",
                str(script),
                "--lang",
                "en",
                "--output",
                str(output),
            ]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(
                narrate, "run_edge_tts", return_value=False
            ):
                with self.assertRaises(SystemExit) as raised:
                    narrate.main()
            self.assertEqual(raised.exception.code, 1)
            self.assertFalse(output.exists())

    def test_main_refuses_to_overwrite_output(self):
        with tempfile.TemporaryDirectory(prefix="narrate_overwrite_") as temp:
            temp_path = Path(temp)
            script = temp_path / "script.txt"
            output = temp_path / "narration.wav"
            script.write_text("Narration.\n", encoding="utf-8")
            output.write_bytes(b"keep")
            argv = [
                "narrate.py",
                "--script",
                str(script),
                "--output",
                str(output),
            ]
            with mock.patch.object(sys, "argv", argv):
                with self.assertRaises(SystemExit) as raised:
                    narrate.main()
            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(output.read_bytes(), b"keep")

    def test_failure_path_is_safe_on_cp950_console(self):
        with tempfile.TemporaryDirectory(prefix="narrate_cp950_") as temp:
            temp_path = Path(temp)
            script = temp_path / "script.txt"
            output = temp_path / "narration.wav"
            script.write_text("Fail safely.\n", encoding="utf-8")
            code = (
                "import sys;"
                f"sys.path.insert(0, {str(SCRIPTS)!r});"
                "import narrate;"
                "narrate.run_edge_tts=lambda *args: False;"
                f"sys.argv=['narrate.py','--script',{str(script)!r},'--lang','en','--output',{str(output)!r}];"
                "narrate.main()"
            )
            environment = os.environ.copy()
            environment["PYTHONIOENCODING"] = "cp950"
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            result = subprocess.run(
                [sys.executable, "-c", code],
                text=True,
                encoding="cp950",
                errors="replace",
                capture_output=True,
                env=environment,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("TTS failed", result.stderr)
            self.assertNotIn("UnicodeEncodeError", result.stderr)


class ThumbnailTests(unittest.TestCase):
    def test_thumbnail_refuses_overwrite_without_force(self):
        with tempfile.TemporaryDirectory(prefix="thumbnail_overwrite_") as temp:
            temp_path = Path(temp)
            background = temp_path / "background.png"
            output = temp_path / "thumbnail.jpg"
            Image.new("RGB", (640, 360), (20, 40, 60)).save(background)
            output.write_bytes(b"keep")

            with self.assertRaises(FileExistsError):
                thumbnail.create_thumbnail(background, "Title", output_path=output)
            self.assertEqual(output.read_bytes(), b"keep")

            thumbnail.create_thumbnail(background, "Title", output_path=output, force=True)
            self.assertGreater(output.stat().st_size, 1000)


class WhisperCliWrapperTests(unittest.TestCase):
    def setUp(self):
        self.shell = shutil.which("pwsh") or shutil.which("powershell")
        if not self.shell:
            self.skipTest("PowerShell is required")

    def test_wrapper_builds_whisper_cpp_arguments_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="whisper_wrapper_") as temp:
            work = Path(temp)
            audio = work / "input.wav"
            model = work / "ggml-model.bin"
            fake_cli = work / "fake-whisper-cli.ps1"
            output_prefix = work / "subtitles" / "caption"
            audio.write_bytes(b"RIFF")
            model.write_bytes(b"model")
            fake_cli.write_text(
                """
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)
$outputIndex = [Array]::IndexOf($Rest, "--output-file")
$languageIndex = [Array]::IndexOf($Rest, "--language")
if ($outputIndex -lt 0 -or $languageIndex -lt 0) { exit 9 }
Set-Content -LiteralPath ($Rest[$outputIndex + 1] + ".srt") -Value $Rest[$languageIndex + 1]
""".strip(),
                encoding="utf-8",
            )

            command = [
                self.shell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(SCRIPTS / "whisper-cli.ps1"),
                str(audio),
                "-WhisperCliPath",
                str(fake_cli),
                "-ModelPath",
                str(model),
                "-Language",
                "zh",
                "-OutputPrefix",
                str(output_prefix),
            ]
            first = subprocess.run(
                command,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(output_prefix.with_suffix(".srt").read_text().strip(), "zh")

            second = subprocess.run(
                command,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("Output already exists", second.stdout + second.stderr)

            translate = subprocess.run(
                command + ["-Task", "translate"],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )
            self.assertNotEqual(translate.returncode, 0)
            self.assertIn(
                "translation is disabled",
                translate.stdout + translate.stderr,
            )

            bypass = subprocess.run(
                command + ["-Force", "--translate"],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )
            self.assertNotEqual(bypass.returncode, 0)
            self.assertIn(
                "translation flags are disabled",
                bypass.stdout + bypass.stderr,
            )

            failing_cli = work / "failing-whisper-cli.ps1"
            failing_cli.write_text("exit 7", encoding="utf-8")
            existing_output = output_prefix.with_suffix(".srt")
            existing_output.write_text("keep-old-output", encoding="utf-8")
            failing_command = [
                self.shell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(SCRIPTS / "whisper-cli.ps1"),
                str(audio),
                "-WhisperCliPath",
                str(failing_cli),
                "-ModelPath",
                str(model),
                "-Language",
                "zh",
                "-OutputPrefix",
                str(output_prefix),
                "-Force",
            ]
            failed_force = subprocess.run(
                failing_command,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )
            self.assertNotEqual(failed_force.returncode, 0)
            self.assertEqual(
                existing_output.read_text(encoding="utf-8"),
                "keep-old-output",
            )

            directory_output = work / "directory-output"
            directory_output.mkdir()
            directory_command = [
                self.shell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(SCRIPTS / "whisper-cli.ps1"),
                str(audio),
                "-WhisperCliPath",
                str(fake_cli),
                "-ModelPath",
                str(model),
                "-OutputPrefix",
                str(directory_output.with_suffix("")),
                "-Force",
            ]
            directory_output.with_suffix(".srt").mkdir()
            rejected_directory = subprocess.run(
                directory_command,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )
            self.assertNotEqual(rejected_directory.returncode, 0)
            self.assertIn(
                "must be a file, not a directory",
                rejected_directory.stdout + rejected_directory.stderr,
            )


class QwenVoiceCloneWrapperTests(unittest.TestCase):
    def setUp(self):
        self.shell = shutil.which("pwsh") or shutil.which("powershell")
        if not self.shell:
            self.skipTest("PowerShell is required")

    def test_wrapper_rejects_ambiguous_text_input_and_existing_output(self):
        with tempfile.TemporaryDirectory(prefix="qwen_voice_clone_wrapper_") as temp:
            work = Path(temp)
            text_file = work / "target.txt"
            reference = work / "reference.wav"
            model = work / "talker.gguf"
            codec = work / "codec.gguf"
            output = work / "output.wav"
            text_file.write_text("Target from file.", encoding="utf-8")
            reference.write_bytes(b"RIFF")
            model.write_bytes(b"model")
            codec.write_bytes(b"codec")
            output.write_bytes(b"keep")

            base_command = [
                self.shell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(SCRIPTS / "qwen-voice-clone.ps1"),
                "-ReferenceWav",
                str(reference),
                "-OutputPath",
                str(output),
                "-ModelPath",
                str(model),
                "-CodecPath",
                str(codec),
                "-QwenTtsPath",
                sys.executable,
            ]
            ambiguous = subprocess.run(
                base_command + ["-Text", "Direct target.", "-TextFile", str(text_file)],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )
            self.assertNotEqual(ambiguous.returncode, 0)
            self.assertIn("exactly one of -Text or -TextFile", ambiguous.stdout + ambiguous.stderr)

            blocked = subprocess.run(
                base_command + ["-Text", "Direct target."],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("Output already exists", blocked.stdout + blocked.stderr)
            self.assertEqual(output.read_bytes(), b"keep")


class QwenNarrationPipelineTests(unittest.TestCase):
    def setUp(self):
        self.shell = shutil.which("pwsh") or shutil.which("powershell")
        if not self.shell:
            self.skipTest("PowerShell is required")

    def run_pipeline(self, *arguments, env=None):
        return subprocess.run(
            [
                self.shell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(SCRIPTS / "qwen-narration-pipeline.ps1"),
                *map(str, arguments),
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
        )

    def make_fake_wrappers(self, work):
        qwen = work / "fake-qwen.ps1"
        whisper = work / "fake-whisper.ps1"
        qwen.write_text(
            """
param(
    [string]$Text,
    [string]$TextFile,
    [string]$ReferenceWav,
    [string]$ReferenceText,
    [string]$ReferenceTextFile,
    [string]$OutputPath,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest
)
Add-Content -LiteralPath $env:QWEN_NARRATION_TEST_LOG -Value "qwen|$OutputPath"
Set-Content -LiteralPath $OutputPath -Value "RIFF-qwen"
""".strip(),
            encoding="utf-8",
        )
        whisper.write_text(
            """
param(
    [Parameter(Position = 0)][string]$InputPath,
    [string]$OutputPrefix,
    [string]$Language,
    [string]$Task,
    [string]$Format,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest
)
Add-Content -LiteralPath $env:QWEN_NARRATION_TEST_LOG -Value "$Task|$Language|$OutputPrefix.$Format"
if ($env:QWEN_NARRATION_FAIL_TASK -eq $Task) { throw "forced $Task failure" }
Set-Content -LiteralPath "$OutputPrefix.$Format" -Value "$Task result"
""".strip(),
            encoding="utf-8",
        )
        return qwen, whisper

    def test_generates_audio_then_transcribes_for_agent_translation(self):
        with tempfile.TemporaryDirectory(prefix="qwen_narration_pipeline_") as temp:
            work = Path(temp)
            reference = work / "reference.wav"
            text_file = work / "narration.txt"
            output = work / "narration.wav"
            log = work / "pipeline.log"
            reference.write_bytes(b"RIFF-reference")
            text_file.write_text("這是一段測試旁白。", encoding="utf-8")
            qwen, whisper = self.make_fake_wrappers(work)
            env = os.environ.copy()
            env["QWEN_NARRATION_TEST_LOG"] = str(log)

            result = self.run_pipeline(
                "-TextFile",
                text_file,
                "-ReferenceWav",
                reference,
                "-ReferenceText",
                "參考聲音內容。",
                "-OutputPath",
                output,
                "-WhisperLanguage",
                "zh",
                "-QwenWrapperPath",
                qwen,
                "-WhisperWrapperPath",
                whisper,
                "-ConfirmVoiceRights",
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            transcript = work / "narration.asr.srt"
            self.assertTrue(output.is_file())
            self.assertTrue(transcript.is_file())
            calls = log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(calls[0].split("|", 1)[0], "qwen")
            self.assertEqual(calls[1].split("|", 1)[0], "transcribe")
            self.assertEqual(len(calls), 2)
            self.assertIn("|zh|", calls[1])
            self.assertIn(
                "translate the transcript with the active Agent",
                result.stdout,
            )

    def test_fails_closed_when_transcription_fails(self):
        with tempfile.TemporaryDirectory(prefix="qwen_narration_failure_") as temp:
            work = Path(temp)
            reference = work / "reference.wav"
            output = work / "narration.wav"
            log = work / "pipeline.log"
            reference.write_bytes(b"RIFF-reference")
            qwen, whisper = self.make_fake_wrappers(work)
            env = os.environ.copy()
            env["QWEN_NARRATION_TEST_LOG"] = str(log)
            env["QWEN_NARRATION_FAIL_TASK"] = "transcribe"

            result = self.run_pipeline(
                "-Text",
                "這是一段測試旁白。",
                "-ReferenceWav",
                reference,
                "-ReferenceText",
                "參考聲音內容。",
                "-OutputPath",
                output,
                "-QwenWrapperPath",
                qwen,
                "-WhisperWrapperPath",
                whisper,
                "-ConfirmVoiceRights",
                env=env,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("forced transcribe failure", result.stdout + result.stderr)
            self.assertFalse(output.exists())
            self.assertFalse((work / "narration.asr.srt").exists())

    def test_requires_voice_rights_and_refuses_existing_artifacts(self):
        with tempfile.TemporaryDirectory(prefix="qwen_narration_safety_") as temp:
            work = Path(temp)
            reference = work / "reference.wav"
            output = work / "narration.wav"
            reference.write_bytes(b"RIFF-reference")
            output.write_bytes(b"keep")
            qwen, whisper = self.make_fake_wrappers(work)

            no_rights = self.run_pipeline(
                "-Text",
                "旁白。",
                "-ReferenceWav",
                reference,
                "-ReferenceText",
                "參考。",
                "-OutputPath",
                work / "new.wav",
                "-QwenWrapperPath",
                qwen,
                "-WhisperWrapperPath",
                whisper,
            )
            self.assertNotEqual(no_rights.returncode, 0)
            self.assertIn("ConfirmVoiceRights", no_rights.stdout + no_rights.stderr)

            blocked = self.run_pipeline(
                "-Text",
                "旁白。",
                "-ReferenceWav",
                reference,
                "-ReferenceText",
                "參考。",
                "-OutputPath",
                output,
                "-QwenWrapperPath",
                qwen,
                "-WhisperWrapperPath",
                whisper,
                "-ConfirmVoiceRights",
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("Output already exists", blocked.stdout + blocked.stderr)
            self.assertEqual(output.read_bytes(), b"keep")


class AgentTranslationValidationTests(unittest.TestCase):
    def run_validator(self, source, translation):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "validate_agent_translation.py"),
                str(source),
                str(translation),
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )

    def test_accepts_agent_translation_with_preserved_timing(self):
        with tempfile.TemporaryDirectory(prefix="agent_translation_") as temp:
            work = Path(temp)
            source = work / "narration.asr.srt"
            translation = work / "narration.en.srt"
            source.write_text(
                "1\n00:00:00,000 --> 00:00:02,000\n歡迎收看\n\n",
                encoding="utf-8",
            )
            translation.write_text(
                "1\n00:00:00,000 --> 00:00:02,000\nWelcome.\n\n",
                encoding="utf-8",
            )

            result = self.run_validator(source, translation)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("timestamps preserved", result.stdout)

    def test_rejects_changed_timing_and_non_english_output(self):
        with tempfile.TemporaryDirectory(prefix="agent_translation_invalid_") as temp:
            work = Path(temp)
            source = work / "narration.asr.srt"
            translation = work / "narration.en.srt"
            source.write_text(
                "1\n00:00:00,000 --> 00:00:02,000\n歡迎收看\n\n",
                encoding="utf-8",
            )
            translation.write_text(
                "1\n00:00:00,100 --> 00:00:02,000\n這不是英文\n\n",
                encoding="utf-8",
            )

            changed_timing = self.run_validator(source, translation)
            self.assertNotEqual(changed_timing.returncode, 0)
            self.assertIn("timestamp changed", changed_timing.stderr)

            translation.write_text(
                "1\n00:00:00,000 --> 00:00:02,000\n這不是英文\n\n",
                encoding="utf-8",
            )
            non_english = self.run_validator(source, translation)
            self.assertNotEqual(non_english.returncode, 0)
            self.assertIn("not English-dominant", non_english.stderr)

    def test_rejects_extra_markdown_or_malformed_blocks(self):
        with tempfile.TemporaryDirectory(prefix="agent_translation_strict_") as temp:
            work = Path(temp)
            source = work / "narration.asr.srt"
            translation = work / "narration.en.srt"
            source.write_text(
                "1\n00:00:00,000 --> 00:00:02,000\n歡迎收看\n\n",
                encoding="utf-8",
            )
            translation.write_text(
                "Here is the translation:\n\n"
                "1\n00:00:00,000 --> 00:00:02,000\nWelcome.\n\n",
                encoding="utf-8",
            )

            result = self.run_validator(source, translation)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Invalid SRT block", result.stderr)

    def test_accepts_english_with_latin_diacritics(self):
        with tempfile.TemporaryDirectory(prefix="agent_translation_latin_") as temp:
            work = Path(temp)
            source = work / "narration.asr.srt"
            translation = work / "narration.en.srt"
            source.write_text(
                "1\n00:00:00,000 --> 00:00:02,000\n咖啡\n\n",
                encoding="utf-8",
            )
            translation.write_text(
                "1\n00:00:00,000 --> 00:00:02,000\nCafé.\n\n",
                encoding="utf-8",
            )

            result = self.run_validator(source, translation)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class AgentTranslationWorkflowContractTests(unittest.TestCase):
    def test_full_pipeline_is_agent_orchestrated_and_fails_closed(self):
        workflow = (ROOT / "workflows" / "full-pipeline.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Agent 編排流程", workflow)
        self.assertIn("validate_agent_translation.py $zhSrt $enSrt", workflow)
        self.assertIn("if ($LASTEXITCODE -ne 0)", workflow)
        self.assertNotIn("AgentPhase", workflow)
        self.assertNotIn("agent-translation.json", workflow)

    def test_batch_pipeline_fails_closed_and_tracks_ffmpeg_inputs(self):
        workflow = (ROOT / "workflows" / "batch-processing.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Agent 應在", workflow)
        self.assertIn('-map 0:v -map "[aout]"', workflow)
        self.assertIn("失敗檔計入", workflow)
        self.assertNotIn("$buildArgs.Count - 2", workflow)
        self.assertNotIn("AgentPhase", workflow)


class AutoEditorWrapperTests(unittest.TestCase):
    def setUp(self):
        self.shell = shutil.which("pwsh") or shutil.which("powershell")
        if not self.shell:
            self.skipTest("PowerShell is required")

    def run_wrapper(self, *arguments, env=None):
        return subprocess.run(
            [
                self.shell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(SCRIPTS / "auto-edit.ps1"),
                *map(str, arguments),
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
        )

    def test_preview_uses_balanced_profile_without_rendering(self):
        with tempfile.TemporaryDirectory(prefix="auto_editor_preview_") as temp:
            work = Path(temp)
            source = work / "input clip.mp4"
            output = work / "edited.mp4"
            log = work / "arguments.txt"
            fake_cli = work / "fake-auto-editor.ps1"
            source.write_bytes(b"video")
            fake_cli.write_text(
                """
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)
$Rest | Set-Content -LiteralPath $env:AUTO_EDITOR_TEST_LOG -Encoding UTF8
if ($Rest -contains "--preview") {
    Write-Output "preview complete"
    exit 0
}
$outputIndex = [Array]::IndexOf($Rest, "-o")
if ($outputIndex -ge 0) {
    Set-Content -LiteralPath $Rest[$outputIndex + 1] -Value "rendered"
}
""".strip(),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["AUTO_EDITOR_TEST_LOG"] = str(log)

            result = self.run_wrapper(
                "-InputPath",
                source,
                "-OutputPath",
                output,
                "-Mode",
                "Preview",
                "-Profile",
                "Balanced",
                "-AutoEditorPath",
                fake_cli,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            arguments = log.read_text(encoding="utf-8-sig").splitlines()
            self.assertIn("--preview", arguments)
            self.assertIn("--edit", arguments)
            self.assertIn("audio:-28dB", arguments)
            self.assertIn("--margin", arguments)
            self.assertIn("0.25sec,0.35sec", arguments)
            self.assertIn("--smooth", arguments)
            self.assertIn("0.25sec,0.10sec", arguments)
            self.assertFalse(output.exists())

    def test_render_refuses_overwrite_and_validates_output(self):
        with tempfile.TemporaryDirectory(prefix="auto_editor_render_") as temp:
            work = Path(temp)
            source = work / "input.mp4"
            output = work / "edited.mp4"
            log = work / "arguments.txt"
            fake_cli = work / "fake-auto-editor.ps1"
            source.write_bytes(b"video")
            output.write_bytes(b"keep")
            fake_cli.write_text(
                """
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)
$Rest | Set-Content -LiteralPath $env:AUTO_EDITOR_TEST_LOG -Encoding UTF8
$outputIndex = [Array]::IndexOf($Rest, "-o")
if ($outputIndex -lt 0) { exit 9 }
Set-Content -LiteralPath $Rest[$outputIndex + 1] -Value "rendered"
if ($env:AUTO_EDITOR_TEST_FAIL -eq "1") { exit 7 }
""".strip(),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["AUTO_EDITOR_TEST_LOG"] = str(log)

            blocked = self.run_wrapper(
                "-InputPath",
                source,
                "-OutputPath",
                output,
                "-Mode",
                "Render",
                "-AutoEditorPath",
                fake_cli,
                env=env,
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("Output already exists", blocked.stdout + blocked.stderr)
            self.assertEqual(output.read_bytes(), b"keep")
            self.assertFalse(log.exists())

            dry_run = self.run_wrapper(
                "-InputPath",
                source,
                "-OutputPath",
                output,
                "-Mode",
                "Render",
                "-AutoEditorPath",
                fake_cli,
                "-Force",
                "-WhatIf",
                env=env,
            )
            self.assertEqual(dry_run.returncode, 0, dry_run.stdout + dry_run.stderr)
            self.assertEqual(output.read_bytes(), b"keep")
            self.assertFalse(log.exists())
            self.assertEqual(list(work.glob("edited.mp4.backup-*")), [])

            env["AUTO_EDITOR_TEST_FAIL"] = "1"
            failed = self.run_wrapper(
                "-InputPath",
                source,
                "-OutputPath",
                output,
                "-Mode",
                "Render",
                "-AutoEditorPath",
                fake_cli,
                "-Force",
                env=env,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("failed with exit code 7", failed.stdout + failed.stderr)
            self.assertEqual(output.read_bytes(), b"keep")
            self.assertEqual(list(work.glob("edited.mp4.backup-*")), [])
            self.assertEqual(len(list(work.glob(".edited.auto-editor-*.partial.mp4"))), 1)

            env.pop("AUTO_EDITOR_TEST_FAIL")
            rendered = self.run_wrapper(
                "-InputPath",
                source,
                "-OutputPath",
                output,
                "-Mode",
                "Render",
                "-Profile",
                "Conservative",
                "-AutoEditorPath",
                fake_cli,
                "-Force",
                env=env,
            )
            self.assertEqual(rendered.returncode, 0, rendered.stdout + rendered.stderr)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)
            backups = list(work.glob("edited.mp4.backup-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), b"keep")
            arguments = log.read_text(encoding="utf-8-sig").splitlines()
            self.assertIn("-o", arguments)
            staging = arguments[arguments.index("-o") + 1]
            self.assertRegex(
                staging,
                r"\.edited\.auto-editor-[0-9a-f]{32}\.partial\.mp4$",
            )
            self.assertIn("audio:-34dB", arguments)

    def test_rejects_directory_output_and_wrong_export_extension(self):
        with tempfile.TemporaryDirectory(prefix="auto_editor_output_contract_") as temp:
            work = Path(temp)
            source = work / "input.mp4"
            output_directory = work / "existing-output.mp4"
            fake_cli = work / "fake-auto-editor.ps1"
            source.write_bytes(b"video")
            output_directory.mkdir()
            fake_cli.write_text("exit 0", encoding="utf-8")

            directory_result = self.run_wrapper(
                "-InputPath",
                source,
                "-OutputPath",
                output_directory,
                "-Mode",
                "Render",
                "-AutoEditorPath",
                fake_cli,
                "-Force",
            )
            self.assertNotEqual(directory_result.returncode, 0)
            self.assertIn(
                "OutputPath must be a file, not a directory",
                directory_result.stdout + directory_result.stderr,
            )
            self.assertTrue(output_directory.is_dir())

            extensions = {
                "premiere": ".xml",
                "premiere-otio": ".otio",
                "resolve": ".fcpxml",
                "final-cut-pro": ".fcpxml",
                "shotcut": ".mlt",
                "kdenlive": ".kdenlive",
                "v3": ".v3",
            }
            for export_format, extension in extensions.items():
                with self.subTest(export_format=export_format):
                    result = self.run_wrapper(
                        "-InputPath",
                        source,
                        "-OutputPath",
                        work / f"{export_format}.wrong",
                        "-Mode",
                        "Export",
                        "-ExportFormat",
                        export_format,
                        "-AutoEditorPath",
                        fake_cli,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(
                        f"requires an '{extension}' OutputPath",
                        result.stdout + result.stderr,
                    )


class AutoEditorInstallerContractTests(unittest.TestCase):
    def test_installer_pins_official_release_and_architecture_hashes(self):
        installer = (SCRIPTS / "install-auto-editor.ps1").read_text(encoding="utf-8")
        self.assertIn('$Version = "31.3.2"', installer)
        self.assertIn(
            "BA508838026D2878F598F6D6CECCEBFB113F9AC784ABD8B2F5F0A07B18BB5674",
            installer,
        )
        self.assertIn(
            "5A5DCA5CCD0A7AA8A3423A2F0590235CE70B8319A61EB75E74FDCE2EED6CCE58",
            installer,
        )
        self.assertIn(
            "https://github.com/WyattBlue/auto-editor/releases/download/",
            installer,
        )


@unittest.skipUnless(
    shutil.which("auto-editor") and shutil.which("ffmpeg") and shutil.which("ffprobe"),
    "Auto-Editor and FFmpeg are required",
)
class AutoEditorIntegrationSmokeTests(unittest.TestCase):
    def setUp(self):
        self.shell = shutil.which("pwsh") or shutil.which("powershell")
        if not self.shell:
            self.skipTest("PowerShell is required")
        version = subprocess.run(
            ["auto-editor", "--version"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        if version != "31.3.2":
            self.skipTest(f"Auto-Editor 31.3.2 required, found {version}")

    def run_wrapper(self, *arguments):
        return subprocess.run(
            [
                self.shell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(SCRIPTS / "auto-edit.ps1"),
                *map(str, arguments),
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )

    def test_official_cli_preview_render_and_otio_export(self):
        with tempfile.TemporaryDirectory(prefix="auto_editor_integration_") as temp:
            work = Path(temp)
            source = work / "source.mp4"
            rendered = work / "rendered.mp4"
            exported = work / "timeline.otio"
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=size=320x180:rate=24:duration=2",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000:duration=2",
                    "-shortest",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(source),
                ],
                check=True,
                capture_output=True,
            )

            commands = (
                ["-InputPath", source, "-Mode", "Preview", "-NoCache"],
                [
                    "-InputPath",
                    source,
                    "-OutputPath",
                    rendered,
                    "-Mode",
                    "Render",
                    "-NoCache",
                ],
                [
                    "-InputPath",
                    source,
                    "-OutputPath",
                    exported,
                    "-Mode",
                    "Export",
                    "-ExportFormat",
                    "premiere-otio",
                    "-NoCache",
                ],
            )
            for arguments in commands:
                result = self.run_wrapper(*arguments)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            self.assertGreater(rendered.stat().st_size, 0)
            self.assertGreater(exported.stat().st_size, 0)
            self.assertIn('"OTIO_SCHEMA": "Timeline.1"', exported.read_text())


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required")
class CapcutSmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="youtube_video_editor_")
        self.work = Path(self.temp_dir.name)
        self.video = self.work / "input.mp4"
        self.srt = self.work / "caption.srt"
        self.silent_video = self.work / "silent.mp4"
        self.short_bgm = self.work / "short_bgm.wav"
        self.shell = shutil.which("pwsh") or shutil.which("powershell")
        if not self.shell:
            self.skipTest("PowerShell is required")

        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=320x180:rate=24:duration=2",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=48000:duration=2",
                "-shortest",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(self.video),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=660:sample_rate=48000:duration=0.5",
                str(self.short_bgm),
            ],
            check=True,
            capture_output=True,
        )
        self.srt.write_text(
            "1\n00:00:00,100 --> 00:00:01,500\n測試字幕 Test\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(self.video),
                "-map",
                "0:v:0",
                "-c:v",
                "copy",
                "-an",
                str(self.silent_video),
            ],
            check=True,
            capture_output=True,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_capcut(self, *arguments, expect_success=True):
        result = subprocess.run(
            [
                self.shell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(SCRIPTS / "capcut.ps1"),
                *map(str, arguments),
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        if expect_success and result.returncode != 0:
            self.fail(f"capcut failed ({result.returncode}):\n{result.stdout}\n{result.stderr}")
        return result

    def test_trim_subtitle_speed_and_overwrite_protection(self):
        trimmed = self.work / "trimmed.mp4"
        subbed = self.work / "subbed.mp4"
        sped = self.work / "sped.mp4"

        self.run_capcut("trim", self.video, "-Start", "0", "-End", "1", "-Output", trimmed)
        self.run_capcut("subtitle", trimmed, "-Srt", self.srt, "-Output", subbed)
        self.run_capcut("speed", subbed, "-Rate", "1.25", "-Output", sped)

        for output in (trimmed, subbed, sped):
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)

        validation = subprocess.run(
            [
                self.shell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(SCRIPTS / "validate.ps1"),
                "-VideoPath",
                str(self.video),
                "-SrtPath",
                str(self.srt),
                "-OutputPath",
                str(sped),
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)

        blocked = self.run_capcut(
            "trim",
            self.video,
            "-Start",
            "0",
            "-End",
            "1",
            "-Output",
            trimmed,
            expect_success=False,
        )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("Output already exists", blocked.stdout)

        self.run_capcut(
            "trim",
            self.video,
            "-Start",
            "0",
            "-End",
            "1",
            "-Output",
            trimmed,
            "-Force",
        )

    def test_merge_text_audio_export_and_info(self):
        merged = self.work / "merged.mp4"
        titled = self.work / "titled.mp4"
        mixed = self.work / "mixed.mp4"
        exported = self.work / "exported.mp4"

        self.run_capcut("merge", f"{self.video},{self.video}", "-Output", merged)
        self.run_capcut("text", merged, "-Text", "Smoke Test", "-Output", titled)
        self.run_capcut("audio", titled, "-Bgm", self.video, "-Output", mixed)
        self.run_capcut("export", mixed, "-Output", exported)
        info = self.run_capcut("info", exported)

        for output in (merged, titled, mixed, exported):
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)
        self.assertIn("Video Info", info.stdout)

    def test_split_slow_speed_and_bgm_for_silent_video(self):
        slowed = self.work / "slowed.mp4"
        with_bgm = self.work / "silent_with_bgm.mp4"

        self.run_capcut("split", self.video, "-At", "1")
        self.run_capcut("speed", self.video, "-Rate", "0.25", "-Output", slowed)
        self.run_capcut("audio", self.silent_video, "-Bgm", self.short_bgm, "-Output", with_bgm)

        self.assertTrue((self.work / "input_part1.mp4").is_file())
        self.assertTrue((self.work / "input_part2.mp4").is_file())
        self.assertTrue(slowed.is_file())
        self.assertTrue(with_bgm.is_file())
        duration = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(with_bgm),
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertGreater(float(duration.stdout.strip()), 1.8)


if __name__ == "__main__":
    unittest.main()
