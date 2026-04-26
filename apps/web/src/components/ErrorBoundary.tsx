import { Component, type ReactNode } from "react";

export class ErrorBoundary extends Component<{ children: ReactNode }, { error: string }> {
  state = { error: "" };

  static getDerivedStateFromError(error: Error) {
    return { error: error.message };
  }

  componentDidCatch(error: Error) {
    fetch("/api/analytics/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_name: "miniapp_error", properties: { message: error.message } })
    }).catch(() => undefined);
  }

  render() {
    if (this.state.error) {
      return (
        <main className="mx-auto max-w-xl px-4 py-8">
          <div className="rounded-app border border-line bg-white p-4 text-sm text-coral">{this.state.error}</div>
        </main>
      );
    }
    return this.props.children;
  }
}
