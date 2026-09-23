// The page's handle on the worker: send a request, get back its updates.

import type { Request, TableOptions, Update, WorkerMessage } from "./protocol";

export class Engine {
  private worker: Worker;
  private next = 1;
  private waiting = new Map<number, { resolve: (u: Update[]) => void; reject: (e: Error) => void }>();
  readonly ready: Promise<{ options: TableOptions; python: string }>;

  constructor() {
    this.worker = new Worker(new URL("./worker.ts", import.meta.url), { type: "module" });
    this.ready = new Promise((resolve, reject) => {
      this.worker.onmessage = (event: MessageEvent<WorkerMessage>) => {
        const message = event.data;
        if (message.type === "ready") {
          resolve({ options: message.options, python: message.python });
          return;
        }
        if (message.id === null) {
          // Only an error can come without a request: the engine failed to boot.
          reject(new Error(message.type === "error" ? message.message : "the game engine failed to start"));
          return;
        }
        const call = this.waiting.get(message.id);
        this.waiting.delete(message.id);
        if (!call) return;
        if (message.type === "updates") call.resolve(message.updates);
        else call.reject(new Error(message.message));
      };
      this.worker.onerror = (event) => reject(new Error(event.message || "the game engine failed to start"));
    });
    // Resolved against the page, so it works at any path and inside an iframe.
    const base = new URL(import.meta.env.BASE_URL, document.baseURI).href;
    this.worker.postMessage({ type: "boot", base });
  }

  send(request: Request): Promise<Update[]> {
    const id = this.next++;
    return new Promise((resolve, reject) => {
      this.waiting.set(id, { resolve, reject });
      this.worker.postMessage({ ...request, id });
    });
  }
}
