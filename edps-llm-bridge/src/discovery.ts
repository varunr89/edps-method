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
