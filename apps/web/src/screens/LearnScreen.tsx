import { useEffect, useState } from "react";
import { LessonPlayer } from "../components/LessonPlayer";
import { ErrorState, LoadingCard } from "../components/ui";
import { api } from "../lib/api";
import { t } from "../lib/format";
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
        setModuleTitle(plan?.module ? t(plan.module.title, user.interface_language, "Guided lesson") : "Guided lesson");
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load your lesson.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [lessonId, user.interface_language, user.telegram_id]);

  if (loading) {
    return <LoadingCard label="Loading lesson" />;
  }

  if (error) {
    return <ErrorState description={error} onRetry={() => window.location.reload()} />;
  }

  return <LessonPlayer user={user} lesson={lesson} moduleTitle={moduleTitle} onNavigate={onNavigate} onCompleted={() => undefined} />;
}
