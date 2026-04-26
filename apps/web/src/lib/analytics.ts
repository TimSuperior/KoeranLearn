import { api } from "./api";

export function track(event_name: string, payload: { telegram_id?: string; audience_language?: string; properties?: Record<string, unknown> }) {
  void api.trackEvent({ event_name, ...payload }).catch(() => undefined);
}
