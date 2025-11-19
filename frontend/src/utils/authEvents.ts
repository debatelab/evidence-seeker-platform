type UnauthorizedHandler = (error?: unknown) => void;

class AuthEvents {
  private unauthorizedHandlers: Set<UnauthorizedHandler> =
    new Set<UnauthorizedHandler>();

  subscribe(handler: UnauthorizedHandler): void {
    this.unauthorizedHandlers.add(handler);
  }

  unsubscribe(handler: UnauthorizedHandler): void {
    this.unauthorizedHandlers.delete(handler);
  }

  emitUnauthorized(error?: unknown): void {
    this.unauthorizedHandlers.forEach((handler) => {
      try {
        handler(error);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error("Unauthorized handler failed", err);
      }
    });
  }
}

export const authEvents = new AuthEvents();
