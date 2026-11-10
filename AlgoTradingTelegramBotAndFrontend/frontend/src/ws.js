const WS_BASE = "ws://localhost:8000";

export class WSClient {
  constructor(path) {
    this.path = path;
    this.socket = null;
    this.onMessage = null;
    this.reconnectInterval = 3000;
  }

  connect() {
    this.socket = new WebSocket(`${WS_BASE}${this.path}`);

    this.socket.onopen = () => {
      console.log(`WS Connected: ${this.path}`);
    };

    this.socket.onmessage = (event) => {
      if (this.onMessage) {
        try {
          const data = JSON.parse(event.data);
          this.onMessage(data);
        } catch {
          this.onMessage(event.data);
        }
      }
    };

    this.socket.onclose = () => {
      console.log(`WS Closed: ${this.path}. Reconnecting...`);
      setTimeout(() => this.connect(), this.reconnectInterval);
    };

    this.socket.onerror = (error) => {
      console.error(`WS Error: ${this.path}`, error);
      this.socket.close();
    };
  }

  send(data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    }
  }

  close() {
    if (this.socket) {
      this.socket.onclose = null;
      this.socket.close();
    }
  }
}
