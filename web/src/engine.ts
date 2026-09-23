// The page's handle on the worker: send a request, get back its updates.

import type { GameRecord, GameRequest, Request, TableOptions, Update, WorkerMessage } from "./protocol";

export class Engine {
  private worker: Worker;
  private next = 1;
  private waiting = new Map<number, { resolve: (value: unknown) => void; reject: (e: Error) => void }>();
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
        else if (message.type === "text") call.resolve(message.text);
        else call.reject(new Error(message.message));
      };
      this.worker.onerror = (event) => reject(new Error(event.message || "the game engine failed to start"));
    });
    // Resolved against the page, so it works at any path and inside an iframe.
    const base = new URL(import.meta.env.BASE_URL, document.baseURI).href;
    this.worker.postMessage({ type: "boot", base });
  }

  send(request: GameRequest): Promise<Update[]> {
    return this.call(request);
  }

  /** Finished games as the CSV `python -m succession analyze` reads. */
  exportCsv(records: GameRecord[]): Promise<string> {
    return this.call({ type: "export", records });
  }

  private call<T>(request: Request): Promise<T> {
    const id = this.next++;
    return new Promise<T>((resolve, reject) => {
      this.waiting.set(id, { resolve: resolve as (value: unknown) => void, reject });
      this.worker.postMessage({ ...request, id });
    });
  }
}
