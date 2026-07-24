import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {captionFadeRange} from "../timeline";
import type {TypographyEvent} from "../types";

export const CaptionPage: React.FC<{event: TypographyEvent}> = ({event}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const localDuration = Math.max(1, Math.round((event.end - event.start) * fps));
  const fadeRange = captionFadeRange(localDuration);
  const opacity = fadeRange
    ? interpolate(frame, fadeRange, [0, 1, 1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;

  return (
    <AbsoluteFill style={{justifyContent: "flex-end", alignItems: "center"}}>
      <div
        style={{
          opacity,
          marginBottom: Math.round(height * 0.16),
          maxWidth: "84%",
          color: "white",
          fontFamily: '"Noto Sans TC", "Microsoft JhengHei", sans-serif',
          fontWeight: 900,
          fontSize: Math.round(height * 0.034),
          lineHeight: 1.22,
          textAlign: "center",
          WebkitTextStroke: "5px #111",
          paintOrder: "stroke fill",
          filter: "drop-shadow(0 4px 4px rgba(0,0,0,.35))",
          whiteSpace: "pre-wrap",
        }}
      >
        {event.text}
      </div>
    </AbsoluteFill>
  );
};
