/**
 * Google Sign-In button.
 * Uses Google Identity Services (GIS) for credential flow.
 * Gracefully hidden if VITE_GOOGLE_CLIENT_ID is not configured.
 */
import { useEffect, useRef, useCallback } from "react";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";

export default function GoogleButton({ onCredential, disabled, label = "Continue with Google" }) {
  const divRef = useRef(null);
  const initialized = useRef(false);

  const handleCredentialResponse = useCallback(
    (response) => {
      if (response?.credential) {
        onCredential(response.credential);
      }
    },
    [onCredential],
  );

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || initialized.current) return;

    // Load Google Identity Services script
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if (window.google?.accounts?.id) {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleCredentialResponse,
        });
        if (divRef.current) {
          window.google.accounts.id.renderButton(divRef.current, {
            theme: "filled_black",
            size: "large",
            shape: "pill",
            width: "100%",
            text: "continue_with",
          });
        }
        initialized.current = true;
      }
    };
    document.head.appendChild(script);

    return () => {
      // Cleanup handled by page unload
    };
  }, [handleCredentialResponse]);

  // If no Google Client ID configured, show a styled fallback button
  if (!GOOGLE_CLIENT_ID) {
    return (
      <button
        type="button"
        disabled
        className="flex w-full items-center justify-center gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-slate-400 opacity-50 cursor-not-allowed"
        title="Google Sign-In not configured"
      >
        <svg className="h-5 w-5" viewBox="0 0 24 24">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
        </svg>
        Google Sign-In not configured
      </button>
    );
  }

  return (
    <div>
      <div ref={divRef} className="flex justify-center" />
    </div>
  );
}
