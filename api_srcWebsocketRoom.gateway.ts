import {
  WebSocketGateway,
  WebSocketServer,
  OnGatewayConnection,
  OnGatewayDisconnect,
  SubscribeMessage,
} from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { Logger } from '@nestjs/common';

// Types for better type safety
interface UserPresence {
  userId: string;
  position: [number, number];
  lastSeen: Date;
}

interface ElementUpdatePayload {
  projectId: string;
  element: any;
  action: 'add' | 'update' | 'delete';
  version?: number;
}

interface CursorMovePayload {
  projectId: string;
  position: [number, number];
}

interface ProjectRoom {
  users: Map<string, UserPresence>;
}

@WebSocketGateway(3001, { 
  cors: { 
    origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
    credentials: true 
  },
  transports: ['websocket', 'polling'] // Explicit transports
})
export class CollaborationGateway implements OnGatewayConnection, OnGatewayDisconnect {
  private readonly logger = new Logger(CollaborationGateway.name);
  
  @WebSocketServer() 
  server: Server;

  // Track project rooms and their users
  private projectRooms = new Map<string, ProjectRoom>();

  async handleConnection(client: Socket) {
    this.logger.log(`Client connected: ${client.id}`);
    
    // Add connection metadata
    client.data.connectedAt = new Date();
    client.data.rooms = new Set();
  }

  async handleDisconnect(client: Socket) {
    this.logger.log(`Client disconnected: ${client.id}`);
    
    // Clean up user from all rooms
    client.data.rooms?.forEach((projectId: string) => {
      this.removeUserFromProject(projectId, client.id);
    });
  }

  @SubscribeMessage('join-project')
  async handleJoinProject(client: Socket, projectId: string) {
    try {
      // Validate projectId
      if (!projectId || typeof projectId !== 'string') {
        client.emit('error', { message: 'Invalid project ID' });
        return;
      }

      // Leave previous project if any
      if (client.data.currentProject) {
        await this.handleLeaveProject(client, client.data.currentProject);
      }

      // Join the room
      await client.join(projectId);
      client.data.currentProject = projectId;
      client.data.rooms.add(projectId);

      // Initialize project room if it doesn't exist
      if (!this.projectRooms.has(projectId)) {
        this.projectRooms.set(projectId, { users: new Map() });
      }

      // Add user to project room
      const projectRoom = this.projectRooms.get(projectId)!;
      projectRoom.users.set(client.id, {
        userId: client.id,
        position: [0, 0],
        lastSeen: new Date()
      });

      // Notify others in the project
      client.to(projectId).emit('user-joined', { 
        userId: client.id,
        users: Array.from(projectRoom.users.values())
      });

      // Send current room state to the joining user
      client.emit('project-joined', {
        projectId,
        users: Array.from(projectRoom.users.values())
      });

      this.logger.log(`User ${client.id} joined project ${projectId}`);
    } catch (error) {
      this.logger.error(`Error joining project: ${error.message}`);
      client.emit('error', { message: 'Failed to join project' });
    }
  }

  @SubscribeMessage('leave-project')
  async handleLeaveProject(client: Socket, projectId: string) {
    try {
      await client.leave(projectId);
      this.removeUserFromProject(projectId, client.id);
      
      client.data.rooms.delete(projectId);
      delete client.data.currentProject;
      
      client.emit('project-left', { projectId });
      this.logger.log(`User ${client.id} left project ${projectId}`);
    } catch (error) {
      this.logger.error(`Error leaving project: ${error.message}`);
    }
  }

  @SubscribeMessage('element-update')
  async handleElementUpdate(client: Socket, payload: ElementUpdatePayload) {
    try {
      // Validate payload
      if (!this.validateElementUpdate(payload)) {
        client.emit('error', { message: 'Invalid element update payload' });
        return;
      }

      // Add metadata
      const enhancedPayload = {
        ...payload,
        userId: client.id,
        timestamp: Date.now(),
        version: payload.version || Date.now() // Simple versioning
      };

      // Broadcast to other users in the project
      client.to(payload.projectId).emit('sync-element', enhancedPayload);
      
      this.logger.debug(`Element ${payload.action} by ${client.id} in project ${payload.projectId}`);
    } catch (error) {
      this.logger.error(`Error handling element update: ${error.message}`);
      client.emit('error', { message: 'Failed to process element update' });
    }
  }

  @SubscribeMessage('cursor-move')
  async handleCursorMove(client: Socket, payload: CursorMovePayload) {
    try {
      // Validate payload
      if (!payload.projectId || !Array.isArray(payload.position) || payload.position.length !== 2) {
        return; // Silently fail for cursor updates to avoid spam
      }

      // Update user's cursor position in room state
      const projectRoom = this.projectRooms.get(payload.projectId);
      if (projectRoom?.users.has(client.id)) {
        const user = projectRoom.users.get(client.id)!;
        user.position = payload.position;
        user.lastSeen = new Date();
      }

      // Broadcast to other users
      client.to(payload.projectId).emit('cursor-update', {
        userId: client.id,
        position: payload.position,
        timestamp: Date.now()
      });
    } catch (error) {
      this.logger.error(`Error handling cursor move: ${error.message}`);
    }
  }

  @SubscribeMessage('heartbeat')
  async handleHeartbeat(client: Socket, projectId: string) {
    // Update user's last seen timestamp
    const projectRoom = this.projectRooms.get(projectId);
    if (projectRoom?.users.has(client.id)) {
      projectRoom.users.get(client.id)!.lastSeen = new Date();
    }
  }

  // Helper methods
  private removeUserFromProject(projectId: string, userId: string): void {
    const projectRoom = this.projectRooms.get(projectId);
    if (projectRoom) {
      projectRoom.users.delete(userId);
      
      // Notify other users
      this.server.to(projectId).emit('user-left', { 
        userId,
        users: Array.from(projectRoom.users.values())
      });

      // Clean up empty rooms
      if (projectRoom.users.size === 0) {
        this.projectRooms.delete(projectId);
        this.logger.log(`Project room ${projectId} cleaned up`);
      }
    }
  }

  private validateElementUpdate(payload: any): payload is ElementUpdatePayload {
    return (
      payload &&
      typeof payload.projectId === 'string' &&
      ['add', 'update', 'delete'].includes(payload.action) &&
      payload.element !== undefined
    );
  }

  // Optional: Method to get room statistics
  getRoomStats() {
    const stats: Record<string, number> = {};
    this.projectRooms.forEach((room, projectId) => {
      stats[projectId] = room.users.size;
    });
    return stats;
  }
}
```

## Key Improvements:

1. **Type Safety**: Added TypeScript interfaces for all payloads
2. **Error Handling**: Comprehensive try-catch blocks and validation
3. **State Management**: Track users in rooms with proper cleanup
4. **Logging**: Use NestJS Logger instead of console.log
5. **Security**: Input validation and CORS configuration
6. **Room Management**: Proper join/leave handling with state synchronization
7. **Metadata**: Added timestamps, versioning, and connection metadata
8. **Heartbeat**: Keep-alive mechanism for connection health
9. **Scalability**: Better data structures for room management
10. **Error Reporting**: Structured error responses to clients

## Additional Recommendations:

1. **Add authentication**:
```typescript
// In handleConnection
const token = client.handshake.auth.token;
if (!this.authService.validateToken(token)) {
  client.disconnect();
  return;
}
```

2. **Add rate limiting** for cursor and element updates
3. **Use Redis adapter** for horizontal scaling
4. **Add operational metrics** and monitoring
5. **Implement conflict resolution** for concurrent edits

This modernized version is more robust, maintainable, and production-ready.