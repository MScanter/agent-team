"""
Message bus for agent communication.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional
from uuid import uuid4


class MessageType(str, Enum):
    """Types of messages in the message bus."""

    BROADCAST = "broadcast"  # To all agents
    DIRECT = "direct"  # To specific agent
    PRIVATE = "private"  # Private, not visible to others
    SYSTEM = "system"  # System notifications


@dataclass
class AgentMessage:
    """Message in the agent communication system."""

    id: str = field(default_factory=lambda: str(uuid4()))
    message_type: MessageType = MessageType.BROADCAST
    from_agent_id: Optional[str] = None
    to_agent_id: Optional[str] = None  # None for broadcast
    content: str = ""
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    visible_to: list[str] = field(default_factory=list)  # Empty = visible to all

    def is_visible_to(self, agent_id: str) -> bool:
        """Check if message is visible to a specific agent."""
        if self.message_type == MessageType.PRIVATE:
            return agent_id in [self.from_agent_id, self.to_agent_id]
        if self.visible_to:
            return agent_id in self.visible_to
        return True


MessageHandler = Callable[[AgentMessage], None]


class MessageBus:
    """
    Message bus for agent-to-agent communication.

    Supports broadcast, direct, and private messaging.
    """

    def __init__(self):
        self._messages: list[AgentMessage] = []
        self._handlers: dict[str, list[MessageHandler]] = {}  # agent_id -> handlers
        self._global_handlers: list[MessageHandler] = []

    def subscribe(self, agent_id: str, handler: MessageHandler):
        """Subscribe an agent to receive messages."""
        if agent_id not in self._handlers:
            self._handlers[agent_id] = []
        self._handlers[agent_id].append(handler)

    def subscribe_global(self, handler: MessageHandler):
        """Subscribe to all messages (for logging, etc.)."""
        self._global_handlers.append(handler)

    def unsubscribe(self, agent_id: str):
        """Unsubscribe an agent from messages."""
        self._handlers.pop(agent_id, None)

    async def publish(self, message: AgentMessage):
        """Publish a message to the bus."""
        self._messages.append(message)

        # Notify global handlers
        for handler in self._global_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception:
                pass  # Don't let handler errors break the bus

        # Notify specific agent handlers
        if message.message_type == MessageType.DIRECT and message.to_agent_id:
            # Direct message - only to target
            handlers = self._handlers.get(message.to_agent_id, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception:
                    pass
        elif message.message_type == MessageType.PRIVATE:
            # Private message - only to sender and recipient
            for agent_id in [message.from_agent_id, message.to_agent_id]:
                if agent_id:
                    handlers = self._handlers.get(agent_id, [])
                    for handler in handlers:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(message)
                            else:
                                handler(message)
                        except Exception:
                            pass
        else:
            # Broadcast - to all subscribers
            for agent_id, handlers in self._handlers.items():
                if message.is_visible_to(agent_id):
                    for handler in handlers:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(message)
                            else:
                                handler(message)
                        except Exception:
                            pass

    def broadcast(
        self,
        from_agent_id: str,
        content: str,
        metadata: dict = None,
    ) -> AgentMessage:
        """Create and publish a broadcast message."""
        message = AgentMessage(
            message_type=MessageType.BROADCAST,
            from_agent_id=from_agent_id,
            content=content,
            metadata=metadata or {},
        )
        asyncio.create_task(self.publish(message))
        return message

    def send_direct(
        self,
        from_agent_id: str,
        to_agent_id: str,
        content: str,
        metadata: dict = None,
    ) -> AgentMessage:
        """Create and publish a direct message."""
        message = AgentMessage(
            message_type=MessageType.DIRECT,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            content=content,
            metadata=metadata or {},
        )
        asyncio.create_task(self.publish(message))
        return message

    def send_private(
        self,
        from_agent_id: str,
        to_agent_id: str,
        content: str,
        metadata: dict = None,
    ) -> AgentMessage:
        """Create and publish a private message."""
        message = AgentMessage(
            message_type=MessageType.PRIVATE,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            content=content,
            metadata=metadata or {},
        )
        asyncio.create_task(self.publish(message))
        return message

    def get_messages(
        self,
        agent_id: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        limit: int = 100,
    ) -> list[AgentMessage]:
        """Get messages, optionally filtered."""
        messages = self._messages

        if agent_id:
            messages = [m for m in messages if m.is_visible_to(agent_id)]

        if message_type:
            messages = [m for m in messages if m.message_type == message_type]

        return messages[-limit:]

    def clear(self):
        """Clear all messages."""
        self._messages.clear()
