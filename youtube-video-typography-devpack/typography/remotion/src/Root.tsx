import React from "react";
import {Composition} from "remotion";
import {DynamicTypography} from "./DynamicTypography";
import {calculatePlanMetadata} from "./timeline";
import type {VisualPlan} from "./types";

const defaultPlan: VisualPlan = {
  schemaVersion: "1.0",
  project: {
    width: 1080,
    height: 1920,
    fps: 30,
    duration: 5,
    language: "zh-TW",
  },
  brandId: "default-zh-tw",
  events: [
    {
      id: "demo",
      start: 0,
      end: 3,
      text: "動態字卡 Demo",
      purpose: "punchline",
      emotion: "surprised",
      intensity: 0.9,
      keywords: ["Demo"],
      templateId: "impact-slam",
      strongEffect: true,
      readingPriority: "high",
    },
  ],
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="DynamicTypography"
      component={DynamicTypography}
      width={defaultPlan.project.width}
      height={defaultPlan.project.height}
      fps={defaultPlan.project.fps}
      durationInFrames={Math.ceil(
        defaultPlan.project.duration * defaultPlan.project.fps,
      )}
      defaultProps={defaultPlan}
      calculateMetadata={({props}) => calculatePlanMetadata(props)}
    />
  );
};
