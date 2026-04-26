import type { AdminEntityKey } from "./types";

export const CORE_ENTITIES: AdminEntityKey[] = ["lessons", "vocabulary", "grammar", "scenarios", "dialogues", "exercises", "audio-assets"];
export const SUPPORT_ENTITIES: AdminEntityKey[] = ["paths", "courses", "modules", "example-sentences", "tags", "localization"];

export const ENTITY_LABELS: Record<AdminEntityKey, string> = {
  paths: "Paths",
  courses: "Courses",
  modules: "Modules",
  lessons: "Lessons",
  vocabulary: "Vocabulary",
  grammar: "Grammar",
  scenarios: "Scenarios",
  dialogues: "Dialogues",
  exercises: "Exercises",
  "audio-assets": "Audio Assets",
  "example-sentences": "Example Sentences",
  tags: "Tags",
  localization: "Localization",
  "premium-packs": "Premium Packs",
};

export const ORDERABLE_ENTITIES = new Set<AdminEntityKey>(["paths", "courses", "modules", "lessons", "scenarios", "dialogues", "exercises", "tags", "premium-packs"]);
export const ACCESS_FILTER_ENTITIES = new Set<AdminEntityKey>(["paths", "courses", "modules", "lessons", "vocabulary", "grammar", "scenarios", "dialogues", "exercises"]);
export const TOPIC_FILTER_ENTITIES = new Set<AdminEntityKey>(["lessons", "vocabulary", "scenarios", "exercises"]);
export const LEVEL_FILTER_ENTITIES = new Set<AdminEntityKey>(["paths", "modules", "lessons", "vocabulary", "grammar", "scenarios", "exercises"]);
export const HEALTH_FILTER_ENTITIES = new Set<AdminEntityKey>(["audio-assets"]);

export const SORT_OPTIONS: Record<AdminEntityKey, Array<{ value: string; label: string }>> = {
  paths: [
    { value: "order_index", label: "Order" },
    { value: "updated_at", label: "Updated" },
  ],
  courses: [
    { value: "order_index", label: "Order" },
    { value: "updated_at", label: "Updated" },
  ],
  modules: [
    { value: "order_index", label: "Order" },
    { value: "updated_at", label: "Updated" },
  ],
  lessons: [
    { value: "order_index", label: "Order" },
    { value: "updated_at", label: "Updated" },
  ],
  vocabulary: [
    { value: "korean", label: "Korean" },
    { value: "updated_at", label: "Updated" },
  ],
  grammar: [
    { value: "korean_pattern", label: "Pattern" },
    { value: "updated_at", label: "Updated" },
  ],
  scenarios: [
    { value: "order_index", label: "Order" },
    { value: "updated_at", label: "Updated" },
  ],
  dialogues: [
    { value: "order_index", label: "Order" },
    { value: "updated_at", label: "Updated" },
  ],
  exercises: [
    { value: "order_index", label: "Order" },
    { value: "updated_at", label: "Updated" },
  ],
  "audio-assets": [
    { value: "updated_at", label: "Updated" },
    { value: "published_at", label: "Published" },
    { value: "expires_at", label: "Expires" },
  ],
  "example-sentences": [
    { value: "updated_at", label: "Updated" },
    { value: "id", label: "Created" },
  ],
  tags: [
    { value: "order_index", label: "Order" },
    { value: "updated_at", label: "Updated" },
  ],
  localization: [
    { value: "key", label: "Key" },
    { value: "updated_at", label: "Updated" },
  ],
  "premium-packs": [
    { value: "order_index", label: "Order" },
    { value: "updated_at", label: "Updated" },
  ],
};
