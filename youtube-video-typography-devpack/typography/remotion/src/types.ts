export type Purpose =
  | "normal_dialogue"
  | "important_fact"
  | "number"
  | "warning"
  | "question"
  | "answer"
  | "punchline"
  | "chapter_title"
  | "quotation"
  | "call_to_action";

export type TemplateId =
  | "clean-bottom"
  | "question-pop"
  | "impact-slam"
  | "warning-alert"
  | "big-number"
  | "chapter-title"
  | "quote-card"
  | "cta-card";

export type TypographyEvent = {
  id: string;
  start: number;
  end: number;
  text: string;
  purpose: Purpose;
  emotion: string;
  intensity: number;
  keywords: string[];
  templateId: TemplateId;
  strongEffect: boolean;
  readingPriority: "low" | "normal" | "high";
};

export type VisualPlan = {
  schemaVersion: "1.0";
  project: {
    width: number;
    height: number;
    fps: number;
    duration: number;
    language: string;
  };
  brandId?: string;
  events: TypographyEvent[];
};
