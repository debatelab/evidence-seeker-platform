const COLOR_VARIABLES = {
  primary: "var(--color-primary)",
  primaryHover: "var(--color-primary-hover)",
  primaryForeground: "var(--color-primary-foreground)",
  primarySoft: "var(--color-primary-soft)",
  primaryMuted: "var(--color-primary-muted)",
  primaryBorder: "var(--color-primary-border)",
  primaryStrong: "var(--color-primary-strong)",
};

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        brand: ["Georgia", "serif"],
      },
      colors: {
        primary: {
          DEFAULT: COLOR_VARIABLES.primary,
          hover: COLOR_VARIABLES.primaryHover,
          foreground: COLOR_VARIABLES.primaryForeground,
          strong: COLOR_VARIABLES.primaryStrong,
        },
        "primary-soft": COLOR_VARIABLES.primarySoft,
        "primary-muted": COLOR_VARIABLES.primaryMuted,
        "primary-border": COLOR_VARIABLES.primaryBorder,
      },
    },
  },
  plugins: [],
}
