import type {TypographyEvent, VisualPlan} from "./types";

export const eventFrameRange = (
  event: TypographyEvent,
  fps: number,
): {from: number; durationInFrames: number} => ({
  from: Math.round(event.start * fps),
  durationInFrames: Math.max(1, Math.round((event.end - event.start) * fps)),
});

export const captionFadeRange = (
  durationInFrames: number,
): [number, number, number, number] | null => {
  if (durationInFrames < 4) {
    return null;
  }
  const fadeFrames = Math.min(4, Math.max(1, Math.floor(durationInFrames / 3)));
  return [0, fadeFrames, durationInFrames - fadeFrames, durationInFrames];
};

export const calculatePlanMetadata = (plan: VisualPlan) => ({
  width: plan.project.width,
  height: plan.project.height,
  fps: plan.project.fps,
  durationInFrames: Math.max(
    1,
    Math.ceil(plan.project.duration * plan.project.fps),
  ),
});
