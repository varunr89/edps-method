import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { DiscoveryManager, ServerInfo } from './discovery';

describe('DiscoveryManager', () => {
  const testDir = path.join(os.tmpdir(), 'edps-test-' + Date.now());
  const discoveryPath = path.join(testDir, 'server.json');
  let manager: DiscoveryManager;

  beforeEach(() => {
    fs.mkdirSync(testDir, { recursive: true });
    manager = new DiscoveryManager(discoveryPath);
  });

  afterEach(() => {
    fs.rmSync(testDir, { recursive: true, force: true });
  });

  it('writes server info to discovery file', () => {
    const info: ServerInfo = {
      port: 52341,
      pid: process.pid,
      started: new Date().toISOString(),
      models: ['gpt-5', 'claude-sonnet-4.5']
    };

    manager.write(info);

    const content = JSON.parse(fs.readFileSync(discoveryPath, 'utf-8'));
    expect(content.port).toBe(52341);
    expect(content.models).toContain('gpt-5');
  });

  it('removes discovery file on cleanup', () => {
    manager.write({ port: 1234, pid: 1, started: '', models: [] });
    expect(fs.existsSync(discoveryPath)).toBe(true);

    manager.cleanup();

    expect(fs.existsSync(discoveryPath)).toBe(false);
  });
});
