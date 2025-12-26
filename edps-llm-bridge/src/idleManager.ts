// src/idleManager.ts
export class IdleManager {
  private timeoutMs: number;
  private onShutdown: () => void;
  private timer: NodeJS.Timeout | null = null;

  constructor(timeoutMs: number, onShutdown: () => void) {
    this.timeoutMs = timeoutMs;
    this.onShutdown = onShutdown;
  }

  start(): void {
    this.resetTimer();
  }

  stop(): void {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }

  activity(): void {
    this.resetTimer();
  }

  private resetTimer(): void {
    this.stop();
    this.timer = setTimeout(() => {
      this.onShutdown();
    }, this.timeoutMs);
  }
}
