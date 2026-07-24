import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type {TypographyEvent} from "../types";

const palette: Record<string, string> = {
  "impact-slam": "#FFD84D",
  "warning-alert": "#FF3B30",
  "big-number": "#FFD84D",
  "chapter-title": "#FFFFFF",
  "cta-card": "#7C5CFC",
};

export const TitleCard: React.FC<{event: TypographyEvent}> = ({event}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 13, stiffness: 220}});
  const scale = interpolate(pop, [0, 1], [0.72, 1]);
  const rotate = interpolate(pop, [0, 1], [-3, 0]);
  const compactLength = event.text.replace(/\s+/g, "").length;
  const fontScale = compactLength > 14 ? 0.038 : compactLength > 8 ? 0.045 : 0.052;

  return (
    <AbsoluteFill style={{justifyContent: "center", alignItems: "center"}}>
      <div
        style={{
          transform: `scale(${scale}) rotate(${rotate}deg)`,
          maxWidth: "86%",
          padding: "0.18em 0.35em",
          color: palette[event.templateId] ?? "#FFFFFF",
          fontFamily: '"Noto Sans TC", "Microsoft JhengHei", sans-serif',
          fontSize: Math.round(height * fontScale),
          lineHeight: 1.05,
          fontWeight: 950,
          textAlign: "center",
          WebkitTextStroke: "9px #111",
          paintOrder: "stroke fill",
          filter: "drop-shadow(0 8px 0 rgba(0,0,0,.35))",
          whiteSpace: "pre-wrap",
        }}
      >
        {event.text}
      </div>
    </AbsoluteFill>
  );
};
