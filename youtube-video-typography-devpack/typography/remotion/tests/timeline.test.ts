import assert from "node:assert/strict";
import test from "node:test";
import {
  calculatePlanMetadata,
  captionFadeRange,
  eventFrameRange,
} from "../src/timeline";
import type {TypographyEvent, VisualPlan} from "../src/types";

const event: TypographyEvent = {
  id: "caption-1",
  start: 1.25,
  end: 1.251,
  text: "短字幕",
  purpose: "normal_dialogue",
  emotion: "neutral",
  intensity: 0.3,
  keywords: [],
  templateId: "clean-bottom",
  strongEffect: false,
  readingPriority: "normal",
};

test("short events retain at least one frame", () => {
  assert.deepEqual(eventFrameRange(event, 30), {
    from: 38,
    durationInFrames: 1,
  });
  assert.equal(captionFadeRange(1), null);
  assert.deepEqual(captionFadeRange(4), [0, 1, 3, 4]);
});

test("composition metadata follows the visual plan", () => {
  const plan: VisualPlan = {
    schemaVersion: "1.0",
    project: {
      width: 1080,
      height: 1920,
      fps: 29.97,
      duration: 5.01,
      language: "zh-TW",
    },
    events: [event],
  };
  assert.deepEqual(calculatePlanMetadata(plan), {
    width: 1080,
    height: 1920,
    fps: 29.97,
    durationInFrames: 151,
  });
});
