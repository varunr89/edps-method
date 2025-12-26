import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { BridgeServer } from './server';

describe('BridgeServer', () => {
  let server: BridgeServer;

  beforeEach(async () => {
    server = new BridgeServer();
    await server.start(0); // Port 0 = random available port
  });

  afterEach(async () => {
    await server.stop();
  });

  it('responds to health check', async () => {
    const port = server.getPort();
    const response = await fetch(`http://localhost:${port}/health`);
    const data = await response.json() as { status: string; uptime: number };

    expect(response.status).toBe(200);
    expect(data.status).toBe('ok');
    expect(typeof data.uptime).toBe('number');
  });

  it('returns 404 for unknown routes', async () => {
    const port = server.getPort();
    const response = await fetch(`http://localhost:${port}/unknown`);

    expect(response.status).toBe(404);
  });
});
