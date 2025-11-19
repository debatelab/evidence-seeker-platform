import React from "react";
import logoUrl from "../assets/evidence-seeker-logo.svg";

interface LogoProps {
  showText?: boolean;
  className?: string;
  textClassName?: string;
  iconClassName?: string;
  title?: string;
  subtitle?: string;
}

/**
 * Shared brand mark for Evidence Seeker.
 * The SVG is bundled via Vite so we can use it anywhere in the app.
 */
const Logo: React.FC<LogoProps> = ({
  showText = true,
  className = "",
  textClassName = "text-gray-900",
  iconClassName = "h-10",
  title = "Evidence Seeker",
  subtitle,
}) => {
  return (
    <div className={`flex items-center ${className}`}>
      <img
        src={logoUrl}
        alt="Evidence Seeker"
        className={`w-auto ${iconClassName}`}
      />
      {showText && (
        <div className={`ml-3 leading-tight ${textClassName}`}>
          <p className="brand-title">{title}</p>
          {subtitle ? (
            <p className="text-xs font-medium text-gray-500">{subtitle}</p>
          ) : null}
        </div>
      )}
    </div>
  );
};

export default Logo;
