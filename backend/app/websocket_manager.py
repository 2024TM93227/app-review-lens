"""
WebSocket connection management for real-time updates
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Callable
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for different channels"""
    
    def __init__(self):
        # {channel_name: {connection_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Callbacks for events: {event_type: [callable, ...]}
        self.callbacks: Dict[str, list[Callable]] = {}
    
    async def connect(self, channel: str, connection_id: str, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        if channel not in self.active_connections:
            self.active_connections[channel] = {}
        
        self.active_connections[channel][connection_id] = websocket
        logger.info(f"WebSocket connected: {channel}/{connection_id}")
    
    async def disconnect(self, channel: str, connection_id: str):
        """Disconnect and unregister a WebSocket connection"""
        if channel in self.active_connections:
            if connection_id in self.active_connections[channel]:
                del self.active_connections[channel][connection_id]
                logger.info(f"WebSocket disconnected: {channel}/{connection_id}")
            
            # Clean up empty channels
            if not self.active_connections[channel]:
                del self.active_connections[channel]
    
    async def broadcast(self, channel: str, message: dict):
        """Broadcast message to all connections in a channel"""
        if channel not in self.active_connections:
            return
        
        disconnected = []
        for connection_id, websocket in self.active_connections[channel].items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {channel}/{connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(channel, connection_id)
    
    async def send_to_connection(
        self,
        channel: str,
        connection_id: str,
        message: dict
    ):
        """Send message to a specific connection"""
        if channel not in self.active_connections:
            return
        
        websocket = self.active_connections[channel].get(connection_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to {channel}/{connection_id}: {e}")
                await self.disconnect(channel, connection_id)
    
    async def listen(self, channel: str, connection_id: str, websocket: WebSocket):
        """Listen for incoming messages from a specific connection"""
        try:
            while True:
                data = await websocket.receive_text()
                
                # Parse message format: {action: "...", data: {...}}
                try:
                    message = json.loads(data)
                    action = message.get("action")
                    
                    # Handle ping/pong heartbeat
                    if action == "ping":
                        await websocket.send_json({"action": "pong", "timestamp": datetime.utcnow().isoformat()})
                    
                    # Trigger callbacks
                    if action in self.callbacks:
                        for callback in self.callbacks[action]:
                            try:
                                await callback(channel, connection_id, message.get("data"))
                            except Exception as e:
                                logger.error(f"Callback error for action {action}: {e}")
                
                except json.JSONDecodeError:
                    await websocket.send_json({"error": "Invalid JSON"})
        
        except WebSocketDisconnect:
            await self.disconnect(channel, connection_id)
        except Exception as e:
            logger.error(f"WebSocket error in listen: {e}")
            await self.disconnect(channel, connection_id)
    
    def register_callback(self, action: str, callback: Callable):
        """Register callback for specific action"""
        if action not in self.callbacks:
            self.callbacks[action] = []
        self.callbacks[action].append(callback)
    
    def get_channel_size(self, channel: str) -> int:
        """Get number of active connections in a channel"""
        return len(self.active_connections.get(channel, {}))
    
    def get_all_channels(self) -> Dict[str, int]:
        """Get all channels and their connection counts"""
        return {
            channel: len(connections)
            for channel, connections in self.active_connections.items()
        }


# Global connection manager instance
_connection_manager: ConnectionManager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get global connection manager"""
    return _connection_manager


async def broadcast_job_update(
    job_id: str,
    status: str,
    progress: float,
    message: str,
    **kwargs
):
    """Broadcast job status update to all subscribers"""
    channel = f"jobs:{job_id}"
    message_obj = {
        "event": "progress",
        "job_id": job_id,
        "status": status,
        "progress": progress,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs
    }
    await _connection_manager.broadcast(channel, message_obj)


async def broadcast_dashboard_update(
    app_id: str,
    update_type: str,
    data: dict
):
    """Broadcast dashboard update to all subscribers"""
    channel = f"dashboard:{app_id}"
    message_obj = {
        "event": update_type,
        "app_id": app_id,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await _connection_manager.broadcast(channel, message_obj)
