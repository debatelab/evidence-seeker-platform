export const SUPPORTED_LANGUAGES = [
  { value: "DE", label: "German (DE)" },
  { value: "EN", label: "English (EN)" },
] as const;

export type SupportedLanguageCode =
  (typeof SUPPORTED_LANGUAGES)[number]["value"];

export const DEFAULT_LANGUAGE: SupportedLanguageCode =
  SUPPORTED_LANGUAGES[0].value;

export const getLanguageLabel = (
  code: string | null | undefined
): string | null => {
  if (!code) {
    return null;
  }
  return (
    SUPPORTED_LANGUAGES.find((option) => option.value === code)?.label ?? code
  );
};
