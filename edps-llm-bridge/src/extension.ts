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
