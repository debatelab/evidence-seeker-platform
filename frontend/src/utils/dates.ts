import { DateTime } from "luxon";

export const formatRelativeTime = (
  value?: string | Date | null,
  fallback = "—"
): string => {
  if (!value) return fallback;

  const parsed =
    value instanceof Date
      ? DateTime.fromJSDate(value, { zone: "utc" })
      : DateTime.fromISO(value, { zone: "utc" });

  if (!parsed.isValid) return fallback;

  const relative = parsed.toRelative();
  return relative ?? parsed.toLocaleString(DateTime.DATETIME_MED);
};
