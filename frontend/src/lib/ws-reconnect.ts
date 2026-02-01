/**
 * WebSocket reconnection with exponential backoff and jitter.
 *
 * Usage:
 *   const rc = createReconnect();
 *   ws.onopen  = () => rc.reset();
 *   ws.onclose = () => setTimeout(connect, rc.nextDelay());
 */

export interface ReconnectController {
  /** Get the next reconnection delay in milliseconds. */
  nextDelay(): number;
  /** Reset the attempt counter (call on successful connection). */
  reset(): void;
  /** Current attempt number (0-based). */
  readonly attempt: number;
}

export function createReconnect(
  baseDelay = 1000,
  maxDelay = 30000,
): ReconnectController {
  let _attempt = 0;

  return {
    nextDelay(): number {
      const delay = Math.min(baseDelay * Math.pow(2, _attempt), maxDelay);
      const jitter = delay * 0.1 * Math.random();
      _attempt++;
      return Math.round(delay + jitter);
    },
    reset() {
      _attempt = 0;
    },
    get attempt() {
      return _attempt;
    },
  };
}
