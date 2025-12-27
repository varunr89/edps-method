// src/server.ts
import * as http from 'http';
import { LMClient, CompletionRequest } from './lmClient';

export class BridgeServer {
  private server: http.Server | null = null;
  private port: number = 0;
  private startTime: number = Date.now();
  private lmClient: LMClient | null = null;

  setLMClient(client: LMClient): void {
    this.lmClient = client;
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
