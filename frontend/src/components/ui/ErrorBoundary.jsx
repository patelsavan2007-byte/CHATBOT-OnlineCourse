/**
 * ErrorBoundary - React component catching runtime UI rendering errors.
 * Plain, themed, one link back to the chat.
 */
import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an unhandled error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.href = "/chat";
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="flex min-h-screen flex-col items-center justify-center p-6 text-center"
          style={{ background: "var(--page)", color: "var(--text)" }}
        >
          <div
            className="w-full max-w-md rounded-lg border p-6"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
            }}
          >
            <div
              className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-lg border"
              style={{
                borderColor: "var(--border)",
                background: "var(--surface-2)",
                color: "var(--danger)",
              }}
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h2 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              Something went wrong
            </h2>
            <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
              An unexpected error occurred while rendering this view.
            </p>
            <div className="mt-5">
              <button
                onClick={this.handleReset}
                className="rounded-md px-4 py-2 text-xs font-medium text-white transition hover:opacity-90"
                style={{ background: "var(--accent)" }}
                type="button"
              >
                Return to chat
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
