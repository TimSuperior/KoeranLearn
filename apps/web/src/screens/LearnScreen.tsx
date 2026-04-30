import { useEffect, useState } from "react";
import { LessonPlayer } from "../components/LessonPlayer";
import { ErrorState, LoadingCard } from "../components/ui";
import { api } from "../lib/api";
import { useI18n } from "../lib/i18n";
import type { AppRoute } from "../lib/routes";
import type { AuthUser, Lesson } from "../types";

export function LearnScreen({
  user,
  lessonId,
  onNavigate
}: {
  user: AuthUser;
  lessonId?: number;
  onNavigate: (route: AppRoute) => void;
}) {
  const { content, ui } = useI18n();
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [moduleTitle, setModuleTitle] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");

    Promise.all([
      lessonId
        ? api.startLesson(user.telegram_id, lessonId)
        : api.continueLesson(user.telegram_id).then((next) => (next ? api.startLesson(user.telegram_id, next.id) : next)),
      api.plan().catch(() => null)
    ])
      .then(([lessonValue, plan]) => {
        if (cancelled) return;
        setLesson(lessonValue);
        setModuleTitle(plan?.module ? content(plan.module.title, ui("lesson.guided", "Guided lesson")) : ui("lesson.guided", "Guided lesson"));
      })
      .catch(() => {
        if (!cancelled) setError(ui("lesson.load_error", "Could not load your lesson."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [content, lessonId, ui, user.telegram_id]);

  if (loading) {
    return <LoadingCard label={ui("lesson.loading", "Loading lesson")} />;
  }

  if (error) {
    return <ErrorState description={error} onRetry={() => window.location.reload()} />;
  }

  return <LessonPlayer user={user} lesson={lesson} moduleTitle={moduleTitle} onNavigate={onNavigate} onCompleted={() => undefined} />;
}
