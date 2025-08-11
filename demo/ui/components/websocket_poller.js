import {
  LitElement,
  html,
} from 'https://cdn.jsdelivr.net/gh/lit/dist@3/core/lit-core.min.js';

class WebSocketPoller extends LitElement {
  static properties = {
    triggerEvent: {type: String},
    action: {type: Object},
  };

  constructor() {
    super();
    this.ws = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this.connectWebSocket();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.ws) {
      this.ws.close();
    }
  }

  connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/__ws__`;
    
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.dispatchEvent(
        new MesopEvent(this.triggerEvent, {
          action: data,
        }),
      );
    };

    this.ws.onclose = () => {
      // Reconnect after 1 second if connection is lost
      setTimeout(() => this.connectWebSocket(), 1000);
    };
  }

  render() {
    return html`<div></div>`;
  }
}

customElements.define('websocket-poller', WebSocketPoller);
