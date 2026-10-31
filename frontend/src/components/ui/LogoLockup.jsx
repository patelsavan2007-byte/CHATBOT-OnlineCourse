/**
 * LogoLockup - side-by-side lockup of the CHARUSAT logo and CCOE logo
 * with a 1px vertical divider between them.
 * Used on Login, Signup, Admin Login, and About pages.
 */
import ThemedLogo from "./ThemedLogo.jsx";

export default function LogoLockup({ height = 36, className = "" }) {
  return (
    <div className={`inline-flex items-center justify-center gap-3.5 ${className}`}>
      <ThemedLogo variant="charusat" height={height} />
      <div
        className="h-7 w-px shrink-0"
        style={{ background: "var(--border)" }}
        aria-hidden="true"
      />
      <ThemedLogo variant="ccoe" height={height} />
    </div>
  );
}
