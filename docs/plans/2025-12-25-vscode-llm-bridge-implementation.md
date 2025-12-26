# VS Code LLM Bridge Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a VS Code extension that bridges the Copilot LM API to EDPS Python CLI via HTTP, enabling large context window models for book processing.

**Architecture:** A minimal VS Code extension runs an HTTP server on a dynamic port, writing connection info to `~/.edps/server.json`. The Python client reads this file and makes HTTP requests. Azure remains as fallback.

**Tech Stack:** TypeScript (VS Code Extension), Python (EDPS CLI), HTTP/JSON

---

## Part 1: VS Code Extension

### Task 1: Initialize Extension Project

**Files:**
- Create: `edps-llm-bridge/package.json`
- Create: `edps-llm-bridge/tsconfig.json`
- Create: `edps-llm-bridge/.vscodeignore`
- Create: `edps-llm-bridge/.gitignore`

**Step 1: Create extension directory**

```bash
mkdir -p ~/Projects/edps-llm-bridge
cd ~/Projects/edps-llm-bridge
```

**Step 2: Create package.json**

```json
{
  "name": "edps-llm-bridge",
  "displayName": "EDPS LLM Bridge",
  "description": "HTTP bridge to VS Code Language Model API for EDPS CLI",
  "version": "0.1.0",
  "publisher": "varunr",
  "engines": {
    "vscode": "^1.85.0"
  },
  "categories": ["Other"],
  "activationEvents": ["onStartupFinished"],
  "main": "./out/extension.js",
  "contributes": {
    "commands": [
      {
        "command": "edps-llm-bridge.status",
        "title": "EDPS: LLM Bridge Status"
      }
    ]
  },
  "scripts": {
    "vscode:prepublish": "npm run compile",
    "compile": "tsc -p ./",
    "watch": "tsc -watch -p ./",
    "lint": "eslint src --ext ts",
    "test": "vitest"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/vscode": "^1.85.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "eslint": "^8.0.0",
    "typescript": "^5.3.0",
    "vitest": "^1.0.0"
  }
}
```

**Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "module": "commonjs",
    "target": "ES2022",
    "outDir": "out",
    "lib": ["ES2022"],
    "sourceMap": true,
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "exclude": ["node_modules", ".vscode-test"]
}
```

**Step 4: Create .vscodeignore**

```
.vscode/**
.vscode-test/**
src/**
.gitignore
tsconfig.json
vitest.config.ts
**/*.map
node_modules/**
```

**Step 5: Create .gitignore**

```
out/
node_modules/
*.vsix
.vscode-test/
```

**Step 6: Install dependencies**

```bash
npm install
```

**Step 7: Commit**

```bash
git init
git add .
git commit -m "feat: initialize edps-llm-bridge extension project"
```

---

### Task 2: Create Discovery File Manager

**Files:**
- Create: `edps-llm-bridge/src/discovery.ts`
- Create: `edps-llm-bridge/src/discovery.test.ts`

**Step 1: Write the failing test**

```typescript
// src/discovery.test.ts
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
```

**Step 2: Run test to verify it fails**

```bash
npm test -- src/discovery.test.ts
```

Expected: FAIL with "Cannot find module './discovery'"

**Step 3: Write minimal implementation**

```typescript
// src/discovery.ts
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

export interface ServerInfo {
  port: number;
  pid: number;
  started: string;
  models: string[];
}

export class DiscoveryManager {
  private filePath: string;

  constructor(filePath?: string) {
    this.filePath = filePath ?? path.join(os.homedir(), '.edps', 'server.json');
  }

  write(info: ServerInfo): void {
    const dir = path.dirname(this.filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(this.filePath, JSON.stringify(info, null, 2));
  }

  cleanup(): void {
    if (fs.existsSync(this.filePath)) {
      fs.unlinkSync(this.filePath);
    }
  }

  getPath(): string {
    return this.filePath;
  }
}
```

**Step 4: Run test to verify it passes**

```bash
npm test -- src/discovery.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/discovery.ts src/discovery.test.ts
git commit -m "feat: add discovery file manager"
```

---

### Task 3: Create HTTP Server

**Files:**
- Create: `edps-llm-bridge/src/server.ts`
- Create: `edps-llm-bridge/src/server.test.ts`

**Step 1: Write the failing test**

```typescript
// src/server.test.ts
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { BridgeServer } from './server';
import http from 'http';

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
    const data = await response.json();

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
```

**Step 2: Run test to verify it fails**

```bash
npm test -- src/server.test.ts
```

Expected: FAIL with "Cannot find module './server'"

**Step 3: Write minimal implementation**

```typescript
// src/server.ts
import * as http from 'http';

export class BridgeServer {
  private server: http.Server | null = null;
  private port: number = 0;
  private startTime: number = Date.now();

  async start(port: number = 0): Promise<void> {
    return new Promise((resolve, reject) => {
      this.server = http.createServer((req, res) => {
        this.handleRequest(req, res);
      });

      this.server.listen(port, '127.0.0.1', () => {
        const addr = this.server!.address();
        if (addr && typeof addr === 'object') {
          this.port = addr.port;
        }
        this.startTime = Date.now();
        resolve();
      });

      this.server.on('error', reject);
    });
  }

  async stop(): Promise<void> {
    return new Promise((resolve) => {
      if (this.server) {
        this.server.close(() => resolve());
      } else {
        resolve();
      }
    });
  }

  getPort(): number {
    return this.port;
  }

  private handleRequest(req: http.IncomingMessage, res: http.ServerResponse): void {
    const url = req.url || '/';

    if (url === '/health' && req.method === 'GET') {
      this.handleHealth(res);
    } else if (url === '/models' && req.method === 'GET') {
      this.handleModels(res);
    } else if (url === '/complete' && req.method === 'POST') {
      this.handleComplete(req, res);
    } else {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Not found' }));
    }
  }

  private handleHealth(res: http.ServerResponse): void {
    const uptime = Math.floor((Date.now() - this.startTime) / 1000);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', uptime }));
  }

  private handleModels(res: http.ServerResponse): void {
    // Placeholder - will be populated from vscode.lm
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ models: [] }));
  }

  private handleComplete(req: http.IncomingMessage, res: http.ServerResponse): void {
    // Placeholder - will call vscode.lm
    res.writeHead(501, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Not implemented' }));
  }
}
```

**Step 4: Run test to verify it passes**

```bash
npm test -- src/server.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/server.ts src/server.test.ts
git commit -m "feat: add HTTP server with health endpoint"
```

---

### Task 4: Create LM Client Wrapper

**Files:**
- Create: `edps-llm-bridge/src/lmClient.ts`

**Step 1: Create the LM client wrapper**

```typescript
// src/lmClient.ts
import * as vscode from 'vscode';

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface CompletionRequest {
  model: string;
  messages: ChatMessage[];
  max_tokens?: number;
  temperature?: number;
}

export interface CompletionResponse {
  content: string;
  usage: {
    input_tokens: number;
    output_tokens: number;
  };
}

export class LMClient {
  private models: Map<string, vscode.LanguageModelChat> = new Map();

  async refreshModels(): Promise<string[]> {
    const available = await vscode.lm.selectChatModels();
    this.models.clear();
    for (const model of available) {
      this.models.set(model.id, model);
    }
    return Array.from(this.models.keys());
  }

  getAvailableModels(): string[] {
    return Array.from(this.models.keys());
  }

  async complete(request: CompletionRequest): Promise<CompletionResponse> {
    const model = this.models.get(request.model);
    if (!model) {
      // Try to find by partial match
      const matchingKey = Array.from(this.models.keys()).find(k =>
        k.toLowerCase().includes(request.model.toLowerCase())
      );
      if (matchingKey) {
        return this.complete({ ...request, model: matchingKey });
      }
      throw new Error(`Model not available: ${request.model}. Available: ${this.getAvailableModels().join(', ')}`);
    }

    const messages: vscode.LanguageModelChatMessage[] = request.messages.map(m => {
      if (m.role === 'user') {
        return vscode.LanguageModelChatMessage.User(m.content);
      } else if (m.role === 'assistant') {
        return vscode.LanguageModelChatMessage.Assistant(m.content);
      } else {
        // System messages become user messages with [System] prefix
        return vscode.LanguageModelChatMessage.User(`[System] ${m.content}`);
      }
    });

    const response = await model.sendRequest(messages, {
      maxTokens: request.max_tokens,
    });

    let content = '';
    for await (const chunk of response.text) {
      content += chunk;
    }

    // Estimate tokens (VS Code API doesn't always provide exact counts)
    const inputTokens = request.messages.reduce((sum, m) => sum + Math.ceil(m.content.length / 4), 0);
    const outputTokens = Math.ceil(content.length / 4);

    return {
      content,
      usage: {
        input_tokens: inputTokens,
        output_tokens: outputTokens
      }
    };
  }
}
```

**Step 2: Commit**

```bash
git add src/lmClient.ts
git commit -m "feat: add VS Code LM API client wrapper"
```

---

### Task 5: Create Idle Timeout Manager

**Files:**
- Create: `edps-llm-bridge/src/idleManager.ts`
- Create: `edps-llm-bridge/src/idleManager.test.ts`

**Step 1: Write the failing test**

```typescript
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
```

**Step 2: Run test to verify it fails**

```bash
npm test -- src/idleManager.test.ts
```

Expected: FAIL

**Step 3: Write minimal implementation**

```typescript
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
```

**Step 4: Run test to verify it passes**

```bash
npm test -- src/idleManager.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/idleManager.ts src/idleManager.test.ts
git commit -m "feat: add idle timeout manager"
```

---

### Task 6: Integrate Complete Endpoint with LM Client

**Files:**
- Modify: `edps-llm-bridge/src/server.ts`

**Step 1: Update server to use LM client**

```typescript
// src/server.ts - updated version
import * as http from 'http';
import { LMClient, CompletionRequest } from './lmClient';

export class BridgeServer {
  private server: http.Server | null = null;
  private port: number = 0;
  private startTime: number = Date.now();
  private lmClient: LMClient | null = null;
  private onActivity: (() => void) | null = null;

  setLMClient(client: LMClient): void {
    this.lmClient = client;
  }

  setOnActivity(callback: () => void): void {
    this.onActivity = callback;
  }

  async start(port: number = 0): Promise<void> {
    return new Promise((resolve, reject) => {
      this.server = http.createServer((req, res) => {
        this.handleRequest(req, res);
      });

      this.server.listen(port, '127.0.0.1', () => {
        const addr = this.server!.address();
        if (addr && typeof addr === 'object') {
          this.port = addr.port;
        }
        this.startTime = Date.now();
        resolve();
      });

      this.server.on('error', reject);
    });
  }

  async stop(): Promise<void> {
    return new Promise((resolve) => {
      if (this.server) {
        this.server.close(() => resolve());
      } else {
        resolve();
      }
    });
  }

  getPort(): number {
    return this.port;
  }

  private handleRequest(req: http.IncomingMessage, res: http.ServerResponse): void {
    // Signal activity for idle timeout
    if (this.onActivity) {
      this.onActivity();
    }

    const url = req.url || '/';

    if (url === '/health' && req.method === 'GET') {
      this.handleHealth(res);
    } else if (url === '/models' && req.method === 'GET') {
      this.handleModels(res);
    } else if (url === '/complete' && req.method === 'POST') {
      this.handleComplete(req, res);
    } else {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Not found' }));
    }
  }

  private handleHealth(res: http.ServerResponse): void {
    const uptime = Math.floor((Date.now() - this.startTime) / 1000);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', uptime }));
  }

  private handleModels(res: http.ServerResponse): void {
    const models = this.lmClient?.getAvailableModels() ?? [];
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ models }));
  }

  private async handleComplete(req: http.IncomingMessage, res: http.ServerResponse): Promise<void> {
    if (!this.lmClient) {
      res.writeHead(503, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'LM client not initialized' }));
      return;
    }

    try {
      const body = await this.readBody(req);
      const request: CompletionRequest = JSON.parse(body);

      const response = await this.lmClient.complete(request);

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(response));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: message }));
    }
  }

  private readBody(req: http.IncomingMessage): Promise<string> {
    return new Promise((resolve, reject) => {
      let body = '';
      req.on('data', chunk => body += chunk);
      req.on('end', () => resolve(body));
      req.on('error', reject);
    });
  }
}
```

**Step 2: Commit**

```bash
git add src/server.ts
git commit -m "feat: integrate LM client with HTTP server"
```

---

### Task 7: Create Extension Entry Point

**Files:**
- Create: `edps-llm-bridge/src/extension.ts`

**Step 1: Create extension entry point**

```typescript
// src/extension.ts
import * as vscode from 'vscode';
import { BridgeServer } from './server';
import { LMClient } from './lmClient';
import { DiscoveryManager } from './discovery';
import { IdleManager } from './idleManager';

const IDLE_TIMEOUT_MS = 10 * 60 * 1000; // 10 minutes

let server: BridgeServer | null = null;
let lmClient: LMClient | null = null;
let discovery: DiscoveryManager | null = null;
let idleManager: IdleManager | null = null;
let outputChannel: vscode.OutputChannel | null = null;

function log(message: string): void {
  const timestamp = new Date().toISOString();
  outputChannel?.appendLine(`[${timestamp}] ${message}`);
}

async function startServer(): Promise<void> {
  if (server) {
    log('Server already running');
    return;
  }

  log('Starting EDPS LLM Bridge server...');

  // Initialize components
  lmClient = new LMClient();
  const models = await lmClient.refreshModels();
  log(`Available models: ${models.join(', ')}`);

  server = new BridgeServer();
  server.setLMClient(lmClient);

  discovery = new DiscoveryManager();

  // Setup idle timeout
  idleManager = new IdleManager(IDLE_TIMEOUT_MS, () => {
    log('Idle timeout reached, shutting down server');
    stopServer();
  });

  server.setOnActivity(() => {
    idleManager?.activity();
  });

  // Start server on dynamic port
  await server.start(0);
  const port = server.getPort();

  // Write discovery file
  discovery.write({
    port,
    pid: process.pid,
    started: new Date().toISOString(),
    models
  });

  idleManager.start();

  log(`Server started on port ${port}`);
  log(`Discovery file: ${discovery.getPath()}`);

  vscode.window.showInformationMessage(`EDPS LLM Bridge running on port ${port}`);
}

async function stopServer(): Promise<void> {
  log('Stopping EDPS LLM Bridge server...');

  idleManager?.stop();
  idleManager = null;

  await server?.stop();
  server = null;

  discovery?.cleanup();
  discovery = null;

  lmClient = null;

  log('Server stopped');
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  outputChannel = vscode.window.createOutputChannel('EDPS LLM Bridge');
  context.subscriptions.push(outputChannel);

  log('Extension activating...');

  // Register status command
  const statusCmd = vscode.commands.registerCommand('edps-llm-bridge.status', () => {
    if (server) {
      const port = server.getPort();
      const models = lmClient?.getAvailableModels() ?? [];
      vscode.window.showInformationMessage(
        `EDPS LLM Bridge: Running on port ${port}, ${models.length} models available`
      );
    } else {
      vscode.window.showInformationMessage('EDPS LLM Bridge: Not running');
    }
  });
  context.subscriptions.push(statusCmd);

  // Auto-start server
  try {
    await startServer();
  } catch (error) {
    log(`Failed to start server: ${error}`);
    vscode.window.showErrorMessage(`EDPS LLM Bridge failed to start: ${error}`);
  }

  // Cleanup on deactivation
  context.subscriptions.push({
    dispose: () => {
      stopServer();
    }
  });
}

export function deactivate(): void {
  stopServer();
}
```

**Step 2: Compile and verify**

```bash
npm run compile
```

Expected: No errors

**Step 3: Commit**

```bash
git add src/extension.ts
git commit -m "feat: add extension entry point with auto-start"
```

---

### Task 8: Package Extension

**Files:**
- Modify: `edps-llm-bridge/package.json` (add vsce)

**Step 1: Add packaging script**

Add to package.json scripts:

```json
{
  "scripts": {
    "package": "vsce package --out dist/edps-llm-bridge.vsix"
  },
  "devDependencies": {
    "@vscode/vsce": "^2.22.0"
  }
}
```

**Step 2: Install and package**

```bash
npm install
mkdir -p dist
npm run package
```

**Step 3: Install extension locally**

```bash
code --install-extension dist/edps-llm-bridge.vsix --force
```

**Step 4: Commit**

```bash
git add package.json package-lock.json
git commit -m "feat: add extension packaging"
```

---

## Part 2: Python Client Updates

### Task 9: Add VS Code Config to Python

**Files:**
- Modify: `tools/edps/config.py`

**Step 1: Update config dataclasses**

Add after `AzureConfig`:

```python
@dataclass
class VSCodeConfig:
    """VS Code LLM Bridge configuration."""
    discovery_file: str = "~/.edps/server.json"
    timeout: int = 30  # Request timeout in seconds


@dataclass
class CouncilConfig:
    """LLM Council configuration."""
    enabled: bool = True
    tasks: list = field(default_factory=lambda: ["evaluation"])
    models: list = field(default_factory=lambda: ["gpt-5", "claude-sonnet-4.5", "gemini-3-pro"])
    chair: str = "gpt-5"
    stages: int = 3
```

Update `EdpsConfig`:

```python
@dataclass
class EdpsConfig:
    """Root configuration."""
    provider: str = "vscode"  # "vscode" or "azure"
    azure: AzureConfig = field(default_factory=AzureConfig)
    vscode: VSCodeConfig = field(default_factory=VSCodeConfig)
    council: CouncilConfig = field(default_factory=CouncilConfig)
    models: ModelsConfig = field(default_factory=ModelsConfig)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
```

**Step 2: Update load_config to parse new sections**

Add parsing for vscode and council sections in `load_config()`.

**Step 3: Run existing tests**

```bash
cd tools && python -m pytest tests/ -v
```

**Step 4: Commit**

```bash
git add tools/edps/config.py
git commit -m "feat: add vscode and council config sections"
```

---

### Task 10: Create VS Code Client

**Files:**
- Create: `tools/edps/core/vscode_client.py`
- Create: `tools/tests/test_vscode_client.py`

**Step 1: Write the failing test**

```python
# tools/tests/test_vscode_client.py
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from edps.core.vscode_client import VSCodeClient, VSCodeUnavailableError


class TestVSCodeClient:
    def test_reads_discovery_file(self, tmp_path):
        discovery_file = tmp_path / "server.json"
        discovery_file.write_text(json.dumps({
            "port": 52341,
            "pid": 12345,
            "started": "2025-12-25T10:00:00Z",
            "models": ["gpt-5"]
        }))

        client = VSCodeClient(str(discovery_file))
        info = client._read_discovery_file()

        assert info["port"] == 52341
        assert "gpt-5" in info["models"]

    def test_raises_when_discovery_file_missing(self, tmp_path):
        discovery_file = tmp_path / "nonexistent.json"
        client = VSCodeClient(str(discovery_file))

        with pytest.raises(VSCodeUnavailableError):
            client._read_discovery_file()

    @patch('requests.post')
    def test_complete_calls_server(self, mock_post, tmp_path):
        discovery_file = tmp_path / "server.json"
        discovery_file.write_text(json.dumps({
            "port": 52341,
            "pid": 12345,
            "started": "2025-12-25T10:00:00Z",
            "models": ["gpt-5"]
        }))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": "Hello!",
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }
        mock_post.return_value = mock_response

        client = VSCodeClient(str(discovery_file))
        result = client.complete("Say hello", model="gpt-5")

        assert result["content"] == "Hello!"
        mock_post.assert_called_once()
```

**Step 2: Run test to verify it fails**

```bash
cd tools && python -m pytest tests/test_vscode_client.py -v
```

Expected: FAIL

**Step 3: Write implementation**

```python
# tools/edps/core/vscode_client.py
"""VS Code LLM Bridge client."""
import json
from pathlib import Path
from typing import Optional
import requests


class VSCodeUnavailableError(Exception):
    """Raised when VS Code bridge is not available."""
    pass


class VSCodeClient:
    """Client for VS Code LLM Bridge."""

    def __init__(self, discovery_file: str = "~/.edps/server.json", timeout: int = 30):
        self.discovery_file = Path(discovery_file).expanduser()
        self.timeout = timeout
        self._cached_info: Optional[dict] = None

    def _read_discovery_file(self) -> dict:
        """Read server info from discovery file."""
        if not self.discovery_file.exists():
            raise VSCodeUnavailableError(
                f"Discovery file not found: {self.discovery_file}\n"
                "Make sure VS Code is running with the EDPS LLM Bridge extension."
            )

        try:
            content = self.discovery_file.read_text()
            return json.loads(content)
        except (json.JSONDecodeError, IOError) as e:
            raise VSCodeUnavailableError(f"Failed to read discovery file: {e}")

    def _get_base_url(self) -> str:
        """Get server base URL."""
        info = self._read_discovery_file()
        return f"http://localhost:{info['port']}"

    def health_check(self) -> bool:
        """Check if server is responding."""
        try:
            url = f"{self._get_base_url()}/health"
            response = requests.get(url, timeout=2)
            return response.status_code == 200
        except (requests.RequestException, VSCodeUnavailableError):
            return False

    def get_models(self) -> list[str]:
        """Get available models from server."""
        url = f"{self._get_base_url()}/models"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json().get("models", [])

    def complete(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> dict:
        """Send completion request to VS Code bridge.

        Returns:
            dict with 'content' and 'usage' keys
        """
        url = f"{self._get_base_url()}/complete"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            raise VSCodeUnavailableError(f"Request timed out after {self.timeout}s")
        except requests.ConnectionError:
            raise VSCodeUnavailableError("Cannot connect to VS Code bridge")
        except requests.HTTPError as e:
            if e.response.status_code == 429:
                raise VSCodeUnavailableError("Rate limited by VS Code")
            raise
```

**Step 4: Run test to verify it passes**

```bash
cd tools && python -m pytest tests/test_vscode_client.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/core/vscode_client.py tools/tests/test_vscode_client.py
git commit -m "feat: add VS Code bridge client"
```

---

### Task 11: Update LLMClient with Provider Routing

**Files:**
- Modify: `tools/edps/core/llm.py`

**Step 1: Update LLMClient**

```python
# tools/edps/core/llm.py - updated
"""LLM client with provider routing."""
from dataclasses import dataclass
from typing import Optional

from edps.config import EdpsConfig
from edps.core.tokens import estimate_tokens, estimate_cost
from edps.core.vscode_client import VSCodeClient, VSCodeUnavailableError


@dataclass
class LLMResponse:
    """Response from LLM call."""
    content: str
    input_tokens: int
    output_tokens: int
    cost: float
    model: str
    provider: str = "azure"


@dataclass
class LLMPreview:
    """Preview of what an LLM call will do."""
    prompt: str
    input_tokens: int
    estimated_output_tokens: int
    estimated_cost: float
    model: str


class LLMClient:
    """Client with VS Code primary, Azure fallback."""

    def __init__(self, config: EdpsConfig):
        self.config = config
        self.provider = config.provider
        self.temperature = config.defaults.temperature
        self.max_tokens = config.defaults.max_tokens

        # Initialize VS Code client if primary
        self._vscode_client: Optional[VSCodeClient] = None
        if self.provider == "vscode":
            self._vscode_client = VSCodeClient(
                discovery_file=config.vscode.discovery_file,
                timeout=config.vscode.timeout,
            )

        # Azure client (lazy loaded)
        self._azure_client = None
        self.azure_config = config.azure

    @property
    def default_model(self) -> str:
        if self.provider == "vscode":
            return "gpt-5"  # Default for VS Code
        return self.azure_config.model

    def _get_azure_client(self):
        """Lazy-load the Anthropic Foundry client."""
        if self._azure_client is None:
            from anthropic import AnthropicFoundry
            self._azure_client = AnthropicFoundry(
                api_key=self.azure_config.api_key,
                base_url=self.azure_config.endpoint,
            )
        return self._azure_client

    def preview(
        self,
        prompt: str,
        model: Optional[str] = None,
        estimated_output_tokens: int = 1000,
    ) -> LLMPreview:
        """Preview an LLM call without executing."""
        model = model or self.default_model
        input_tokens = estimate_tokens(prompt)
        cost = estimate_cost(input_tokens, estimated_output_tokens, model)

        return LLMPreview(
            prompt=prompt,
            input_tokens=input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            estimated_cost=cost,
            model=model,
        )

    def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Execute an LLM completion with provider routing."""
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens or self.max_tokens

        # Try VS Code first if configured
        if self.provider == "vscode" and self._vscode_client:
            try:
                return self._complete_vscode(prompt, model, temperature, max_tokens)
            except VSCodeUnavailableError as e:
                # Fall back to Azure if available
                if self.azure_config.api_key:
                    print(f"[Warning] VS Code bridge unavailable: {e}")
                    print("[Fallback] Using Azure")
                    return self._complete_azure(prompt, model, temperature, max_tokens)
                raise

        return self._complete_azure(prompt, model, temperature, max_tokens)

    def _complete_vscode(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Complete via VS Code bridge."""
        result = self._vscode_client.complete(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return LLMResponse(
            content=result["content"],
            input_tokens=result["usage"]["input_tokens"],
            output_tokens=result["usage"]["output_tokens"],
            cost=0.0,  # VS Code/Copilot is included in subscription
            model=model,
            provider="vscode",
        )

    def _complete_azure(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Complete via Azure AI Foundry."""
        client = self._get_azure_client()

        response = client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = estimate_cost(input_tokens, output_tokens, model)

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            model=model,
            provider="azure",
        )
```

**Step 2: Run tests**

```bash
cd tools && python -m pytest tests/ -v
```

**Step 3: Commit**

```bash
git add tools/edps/core/llm.py
git commit -m "feat: add provider routing with VS Code primary, Azure fallback"
```

---

### Task 12: Create Council Implementation

**Files:**
- Create: `tools/edps/core/council.py`
- Create: `tools/tests/test_council.py`

**Step 1: Write the failing test**

```python
# tools/tests/test_council.py
import pytest
from unittest.mock import MagicMock, patch

from edps.core.council import Council, CouncilResult


class TestCouncil:
    def test_stage1_gets_independent_answers(self):
        mock_client = MagicMock()
        mock_client.complete.return_value = MagicMock(content="Answer", provider="vscode")

        council = Council(
            models=["gpt-5", "claude-sonnet-4.5"],
            chair="gpt-5",
            stages=1,  # Just stage 1
        )

        result = council.run("Evaluate this", mock_client)

        assert len(result.stage1) == 2
        assert "gpt-5" in result.stage1
        assert "claude-sonnet-4.5" in result.stage1

    def test_full_council_runs_all_stages(self):
        mock_client = MagicMock()
        call_count = 0

        def mock_complete(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock(content=f"Response {call_count}", provider="vscode")

        mock_client.complete.side_effect = mock_complete

        council = Council(
            models=["m1", "m2", "m3"],
            chair="m1",
            stages=3,
        )

        result = council.run("Evaluate", mock_client)

        # Stage 1: 3 answers, Stage 2: 3 reviews, Stage 3: 1 synthesis = 7
        assert call_count == 7
        assert result.final_answer is not None
```

**Step 2: Write implementation**

```python
# tools/edps/core/council.py
"""LLM Council for multi-model evaluation."""
from dataclasses import dataclass, field
from typing import Optional

from edps.core.llm import LLMClient, LLMResponse


@dataclass
class CouncilResult:
    """Result of council evaluation."""
    stage1: dict[str, str] = field(default_factory=dict)
    stage2: dict[str, str] = field(default_factory=dict)
    final_answer: str = ""
    total_tokens: int = 0


class Council:
    """Multi-model council for evaluation tasks."""

    def __init__(
        self,
        models: list[str],
        chair: str,
        stages: int = 3,
    ):
        self.models = models
        self.chair = chair
        self.stages = stages

    def run(self, prompt: str, client: LLMClient) -> CouncilResult:
        """Run the council evaluation."""
        result = CouncilResult()
        total_tokens = 0

        # Stage 1: Independent answers
        for model in self.models:
            response = client.complete(
                prompt=f"You are participating in a council evaluation.\n\n{prompt}",
                model=model,
            )
            result.stage1[model] = response.content
            total_tokens += response.input_tokens + response.output_tokens

        if self.stages < 2:
            result.final_answer = result.stage1.get(self.chair, "")
            result.total_tokens = total_tokens
            return result

        # Stage 2: Cross-review
        for model in self.models:
            other_answers = {m: a for m, a in result.stage1.items() if m != model}
            review_prompt = (
                "Review the following answers and identify strengths and weaknesses:\n\n"
                + "\n\n".join(f"**{m}**: {a}" for m, a in other_answers.items())
            )
            response = client.complete(prompt=review_prompt, model=model)
            result.stage2[model] = response.content
            total_tokens += response.input_tokens + response.output_tokens

        if self.stages < 3:
            result.final_answer = result.stage1.get(self.chair, "")
            result.total_tokens = total_tokens
            return result

        # Stage 3: Chair synthesis
        synthesis_prompt = (
            "As the chair, synthesize the best final answer based on:\n\n"
            "## Original Prompt\n" + prompt + "\n\n"
            "## Answers\n" + "\n".join(f"**{m}**: {a}" for m, a in result.stage1.items()) + "\n\n"
            "## Reviews\n" + "\n".join(f"**{m}**: {r}" for m, r in result.stage2.items()) + "\n\n"
            "Provide the final, synthesized answer:"
        )
        response = client.complete(prompt=synthesis_prompt, model=self.chair)
        result.final_answer = response.content
        total_tokens += response.input_tokens + response.output_tokens

        result.total_tokens = total_tokens
        return result
```

**Step 3: Run tests**

```bash
cd tools && python -m pytest tests/test_council.py -v
```

**Step 4: Commit**

```bash
git add tools/edps/core/council.py tools/tests/test_council.py
git commit -m "feat: add LLM council for multi-model evaluation"
```

---

### Task 13: Integrate Council with Evaluation

**Files:**
- Modify: `tools/edps/evaluation.py`

**Step 1: Update evaluate_section to use council**

Add council support to `evaluate_section()`:

```python
# At the top of evaluation.py, add:
from edps.core.council import Council

# In evaluate_section(), after building the prompt:
def evaluate_section(...):
    # ... existing code ...

    # Build prompt
    prompt = build_evaluation_prompt(source_text, recall_raw, quiz_raw)

    from edps.core.llm import LLMClient
    client = LLMClient(config)

    # Check if council is enabled for evaluation
    if config.council.enabled and "evaluation" in config.council.tasks:
        council = Council(
            models=config.council.models,
            chair=config.council.chair,
            stages=config.council.stages,
        )
        council_result = council.run(prompt, client)
        response_content = council_result.final_answer
    else:
        response = client.complete(prompt, model=config.models.evaluation, max_tokens=2000)
        response_content = response.content

    # Parse response
    recall_feedback, quiz_feedback = parse_evaluation_response(response_content)
    # ... rest of function ...
```

**Step 2: Run tests**

```bash
cd tools && python -m pytest tests/ -v
```

**Step 3: Commit**

```bash
git add tools/edps/evaluation.py
git commit -m "feat: integrate council with evaluation task"
```

---

### Task 14: Update Model Defaults

**Files:**
- Modify: `tools/edps/config.py`

**Step 1: Update ModelsConfig defaults**

```python
@dataclass
class ModelsConfig:
    """Per-task model overrides."""
    chunking: str = "gpt-5"  # Not LLM-based currently
    summary: str = "gemini-3-pro"  # Large context
    podcast: str = "gpt-5"  # Placeholder
    quiz: str = "claude-sonnet-4.5"  # Quality questions
    claims_synthesis: str = "gpt-5"  # Analytical
    evaluation: str = "gpt-5"  # Used as fallback if council disabled
```

**Step 2: Commit**

```bash
git add tools/edps/config.py
git commit -m "feat: update model defaults for VS Code bridge"
```

---

### Task 15: Add CLI Feedback

**Files:**
- Modify: `tools/edps/commands/generate.py`

**Step 1: Add provider status to output**

Update `_generate_content()` to show provider info:

```python
# After client.complete(), add:
provider_label = f"[{response.provider.upper()}]" if hasattr(response, 'provider') else "[AZURE]"
console.print(f"[dim]{provider_label} Tokens: {response.input_tokens} in, {response.output_tokens} out. Cost: ${response.cost:.4f}[/dim]")
```

**Step 2: Commit**

```bash
git add tools/edps/commands/generate.py
git commit -m "feat: show provider in CLI output"
```

---

### Task 16: End-to-End Test

**Step 1: Ensure VS Code is running with extension**

```bash
code --list-extensions | grep edps-llm-bridge
```

**Step 2: Check discovery file exists**

```bash
cat ~/.edps/server.json
```

**Step 3: Test health endpoint**

```bash
PORT=$(cat ~/.edps/server.json | python3 -c "import sys,json; print(json.load(sys.stdin)['port'])")
curl http://localhost:$PORT/health
```

Expected: `{"status":"ok","uptime":...}`

**Step 4: Test models endpoint**

```bash
curl http://localhost:$PORT/models
```

Expected: `{"models":["gpt-5","claude-sonnet-4.5",...]}`

**Step 5: Run EDPS generate**

```bash
cd /path/to/edps-method
source tools/.venv/bin/activate
PYTHONPATH=tools python -m edps.cli generate wealth-of-nations 002 --type summary -y
```

Expected: Summary generated using VS Code bridge

**Step 6: Final commit**

```bash
git add .
git commit -m "test: verify end-to-end VS Code bridge integration"
```

---

## Summary

| Part | Tasks | Description |
|------|-------|-------------|
| VS Code Extension | 1-8 | Initialize, discovery, server, LM client, idle manager, packaging |
| Python Client | 9-15 | Config, VS Code client, provider routing, council, CLI feedback |
| Testing | 16 | End-to-end verification |

**Total estimated tasks:** 16
**Dependencies:** `requests`, `@vscode/vsce`, `vitest`
