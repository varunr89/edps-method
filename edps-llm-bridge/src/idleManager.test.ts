// src/idleManager.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { IdleManager } from './idleManager';

describe('IdleManager', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('calls shutdown after timeout', () => {
    const onShutdown = vi.fn();
    const manager = new IdleManager(1000, onShutdown); // 1 second timeout

    manager.start();
    expect(onShutdown).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1000);
    expect(onShutdown).toHaveBeenCalledTimes(1);
  });

  it('resets timeout on activity', () => {
    const onShutdown = vi.fn();
    const manager = new IdleManager(1000, onShutdown);

    manager.start();
    vi.advanceTimersByTime(800);
    manager.activity(); // Reset at 800ms

    vi.advanceTimersByTime(800); // Now at 1600ms total, 800ms since reset
    expect(onShutdown).not.toHaveBeenCalled();

    vi.advanceTimersByTime(200); // Now 1000ms since reset
    expect(onShutdown).toHaveBeenCalledTimes(1);
  });

  it('can be stopped', () => {
    const onShutdown = vi.fn();
    const manager = new IdleManager(1000, onShutdown);

    manager.start();
    vi.advanceTimersByTime(500);
    manager.stop();

    vi.advanceTimersByTime(1000);
    expect(onShutdown).not.toHaveBeenCalled();
  });
});
