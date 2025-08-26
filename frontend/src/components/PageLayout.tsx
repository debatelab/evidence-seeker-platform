import React from "react";

type PageLayoutVariant = "wide" | "narrow";

interface PageLayoutProps {
  children: React.ReactNode;
  variant?: PageLayoutVariant;
  className?: string;
}

const PageLayout: React.FC<PageLayoutProps> = ({
  children,
  variant = "wide",
  className = "",
}) => {
  const containerClasses = {
    wide: "max-w-7xl mx-auto py-6 sm:px-6 lg:px-8",
    narrow: "max-w-2xl mx-auto py-6 sm:px-6 lg:px-8",
  };

  return (
    <main className={`${containerClasses[variant]} ${className}`}>
      <div className="px-4 py-6 sm:px-0">{children}</div>
    </main>
  );
};

export default PageLayout;
