/**
 * ThemedLogo - renders official CCOE or CHARUSAT logo based on active theme.
 * Reads resolved theme from ThemeContext (never hides with CSS).
 *
 * Requirements:
 * - Alt text: "CCOE, CHARUSAT" for CCOE logo, "CHARUSAT" for university logo.
 * - Aspect ratios preserved, width and height attributes included.
 * - On dark theme, CCOE logo is rendered inside a neutral plate (padded rectangle
 *   in theme surface color with 1px border and 8px radius).
 */
import { useTheme } from "../../contexts/ThemeContext.jsx";

const CCOE_ASPECT_RATIO = 411 / 226; // ~1.8186
const CHARUSAT_ASPECT_RATIO = 1.0;

export default function ThemedLogo({
  variant = "ccoe",
  height = 32,
  className = "",
  alt,
}) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  if (variant === "charusat") {
    const width = Math.round(height * CHARUSAT_ASPECT_RATIO);
    const src1x = isDark ? "/brand/charusat-dark.png" : "/brand/charusat-light.png";
    const src2x = isDark ? "/brand/charusat-dark@2x.png" : "/brand/charusat-light@2x.png";
    const altText = alt || "CHARUSAT";

    return (
      <img
        src={src1x}
        srcSet={`${src1x} 1x, ${src2x} 2x`}
        alt={altText}
        width={width}
        height={height}
        style={{ height: `${height}px`, width: `${width}px` }}
        className={`shrink-0 object-contain ${className}`}
      />
    );
  }

  // Default: CCOE logo
  const width = Math.round(height * CCOE_ASPECT_RATIO);
  const src1x = isDark ? "/brand/ccoe-dark.png" : "/brand/ccoe-light.png";
  const src2x = isDark ? "/brand/ccoe-dark@2x.png" : "/brand/ccoe-light@2x.png";
  const altText = alt || "CCOE, CHARUSAT";

  const imgElement = (
    <img
      src={src1x}
      srcSet={`${src1x} 1x, ${src2x} 2x`}
      alt={altText}
      width={width}
      height={height}
      style={{ height: `${height}px`, width: `${width}px` }}
      className={`shrink-0 object-contain ${className}`}
    />
  );

  // In dark theme, show CCOE on a neutral plate (surface color, 1px border, 8px radius)
  if (isDark) {
    return (
      <span
        className="inline-flex items-center justify-center rounded-[8px] border p-1"
        style={{
          borderColor: "var(--border)",
          background: "#FAFAF9",
        }}
      >
        {imgElement}
      </span>
    );
  }

  return imgElement;
}
