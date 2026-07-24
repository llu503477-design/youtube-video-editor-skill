import React from "react";
import {AbsoluteFill, Sequence} from "remotion";
import {CaptionPage} from "./components/CaptionPage";
import {TitleCard} from "./components/TitleCard";
import {eventFrameRange} from "./timeline";
import type {VisualPlan} from "./types";

const strongTemplates = new Set([
  "impact-slam",
  "warning-alert",
  "big-number",
  "chapter-title",
  "cta-card",
]);

export const DynamicTypography: React.FC<VisualPlan> = (plan) => {
  const {fps} = plan.project;

  return (
    <AbsoluteFill style={{backgroundColor: "transparent"}}>
      {plan.events.map((event) => {
        const {from, durationInFrames} = eventFrameRange(event, fps);
        return (
          <Sequence key={event.id} from={from} durationInFrames={durationInFrames}>
            {strongTemplates.has(event.templateId) ? (
              <TitleCard event={event} />
            ) : (
              <CaptionPage event={event} />
            )}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
