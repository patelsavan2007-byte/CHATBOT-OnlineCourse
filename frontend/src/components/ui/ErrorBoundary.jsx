/**
 * ErrorBoundary — React component catching runtime UI rendering errors.
 * Renders a user-friendly recovery screen with a reload button.
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
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-[var(--surface-primary)] p-6 text-[var(--text-primary)]">
          <div className="max-w-md rounded-2xl border border-[var(--border-primary)] bg-[var(--surface-hover)] p-6 text-center shadow-lg">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-rose-500/10 text-rose-500">
              <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">Something went wrong</h2>
            <p className="mt-2 text-sm text-[var(--text-tertiary)]">
              An unexpected error occurred while displaying this page.
            </p>
            <button
              onClick={this.handleReset}
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition hover:bg-[var(--accent-primary-hover)] focus-visible:outline-2"
              type="button"
            >
              Reload application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
