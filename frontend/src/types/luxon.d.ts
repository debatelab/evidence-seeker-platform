declare module "luxon" {
  // Minimal Luxon declarations used in the app; falls back to any for simplicity.
  export class DateTime {
    static DATETIME_MED: unknown;
    static fromISO(
      text: string,
      options?: Record<string, unknown>
    ): DateTime;
    static fromJSDate(date: Date, options?: Record<string, unknown>): DateTime;
    static now(): DateTime;
    isValid: boolean;
    toISO(): string | null;
    toFormat(format: string): string;
    toRelative(options?: Record<string, unknown>): string | null;
    toLocaleString(format?: unknown): string;
  }
}
