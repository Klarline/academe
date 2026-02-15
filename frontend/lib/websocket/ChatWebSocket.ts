import { getWsUrl } from '../utils';

export class ChatWebSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private messageHandlers: ((data: any) => void)[] = [];
  private errorHandlers: ((error: any) => void)[] = [];
  private closeHandlers: (() => void)[] = [];
  private openHandlers: (() => void)[] = [];
  private isAuthenticated = false;

  constructor(private token: string) {}

  connect(conversationId?: string) {
    const wsUrl = getWsUrl();
    const url = `${wsUrl}/api/v1/ws/chat`;

    this.ws = new WebSocket(url);

    this.ws.onopen = async () => {
      // Send authentication as first message
      if (this.ws) {
        this.ws.send(JSON.stringify({
          type: 'auth',
          token: this.token
        }));
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle authentication confirmation
        if (data.type === 'connected') {
          this.isAuthenticated = true;
          this.reconnectAttempts = 0;
          this.openHandlers.forEach(handler => handler());
          return;
        }

        // Handle other message types
        if (data.type === 'stream_chunk') {
          this.messageHandlers.forEach(handler => handler({
            type: 'token',
            content: data.chunk,
            metadata: data.metadata
          }));
        } else if (data.type === 'end_streaming') {
          this.messageHandlers.forEach(handler => handler({
            type: 'complete',
            metadata: data.metadata
          }));
        } else if (data.type === 'start_streaming') {
          // Streaming started - no action needed
        } else if (data.type === 'error') {
          console.error('WebSocket server error:', data.message);
          this.errorHandlers.forEach(handler => handler(new Error(data.message)));
        } else {
          this.messageHandlers.forEach(handler => handler(data));
        }
      } catch (error) {
        console.error('Failed to parse message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.errorHandlers.forEach(handler => handler(error));
    };

    this.ws.onclose = () => {
      this.isAuthenticated = false;
      this.closeHandlers.forEach(handler => handler());
      this.attemptReconnect(conversationId);
    };
  }

  private attemptReconnect(conversationId?: string) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.connect(conversationId);
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  sendMessage(message: string, conversationId?: string) {
    if (this.ws?.readyState === WebSocket.OPEN && this.isAuthenticated) {
      this.ws.send(JSON.stringify({ 
        type: 'message',
        content: message,
        conversation_id: conversationId 
      }));
    } else {
      console.warn('WebSocket not ready or not authenticated');
    }
  }

  onMessage(handler: (data: any) => void) {
    this.messageHandlers.push(handler);
    return () => {
      this.messageHandlers = this.messageHandlers.filter(h => h !== handler);
    };
  }

  onError(handler: (error: any) => void) {
    this.errorHandlers.push(handler);
  }

  onClose(handler: () => void) {
    this.closeHandlers.push(handler);
  }

  onOpen(handler: () => void) {
    this.openHandlers.push(handler);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.isAuthenticated = false;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN && this.isAuthenticated;
  }
}
