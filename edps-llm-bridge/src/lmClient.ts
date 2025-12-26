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

    const options: vscode.LanguageModelChatRequestOptions = {};
    if (request.max_tokens !== undefined) {
      options.modelOptions = { maxTokens: request.max_tokens };
    }

    const response = await model.sendRequest(messages, options);

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
