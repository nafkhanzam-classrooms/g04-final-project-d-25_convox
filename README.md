# Convox

Convox is a Python-based real-time communication platform built using TCP sockets, JSON packet messaging, and a modular server/client architecture. This terminal-based prototype now supports social features, enhanced room permissions, friend requests, private messaging, persistent chat history, scheduled broadcasts, presence status, **image and file transfer, session recovery, and chunked media handling**.

## Project Structure

- `server/` - Convox backend, socket acceptor, packet routing, service orchestration, and session management
- `client/` - Terminal client application with improved UX and media upload commands
- `protocol/` - JSON packet builder, parser, and chunking utilities with length-prefixed TCP framing
- `database/` - SQLite storage for users, friends, messages, rooms, broadcasts, requests, sessions, and file transfers
- `rooms/` - Room manager for public, private, invite-only, and match rooms
- `matchmaking/` - Matchmaking queue and automatic match room creation
- `friends/` - Friend request and friend list management
- `scheduler/` - Scheduled broadcast runner and timer helpers
- `presence/` - User presence and status notification support
- `media/` - Image transfer, file transfer, encoding, and storage utilities
- `storage/` - File storage manager with upload/download/temp directories
- `utils/` - Shared logger and timestamp utilities

## Features Implemented

### Phase 1: Foundation
- Multi-client TCP server with packet routing
- JSON packet protocol with length-prefixed framing and validation
- Login and duplicate username prevention
- Global and private room chat with history on join
- Modular architecture separating socket I/O from business logic

### Phase 2: Social & Room Management
- Room creation, join, leave, invite, kick, and delete operations
- Owner-based room permissions
- Friend request flow with add/accept/reject/remove actions
- Friend list retrieval and online/offline status visibility
- Private messaging between users
- SQLite-backed persistence for users, rooms, friends, messages, and broadcasts
- Scheduled broadcast system with timed delivery
- User presence and status updates for friends

### Phase 3: Media & Session Recovery (NEW)
- **Image transfer** to rooms and direct messages (PNG/JPG/JPEG)
- **Generic file transfer system** with chunked delivery
- **Packet chunking** for large files (32KB chunks, configurable)
- **Session recovery and reconnect** - users can restore state after disconnect
- **Session token generation** for secure reconnect
- **Media persistence** in SQLite with transfer history
- **Transfer progress reporting** via TRANSFER_PROGRESS packets
- **Improved terminal client UX** with better formatting and command help
- **Storage manager** organizing uploads/downloads by room and user
- **Chunk reassembly and validation** with missing chunk detection
- **Transfer timeout and cleanup** for stale chunks

## Setup

1. Install Python 3.10 or newer.
2. Open a terminal in the project root (`Progjar`).
3. (Optional) Create a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running Convox

Start the server:
```bash
python server.py
```

Start a client in another terminal:
```bash
python client.py
```

## Client Commands

### Chat & Rooms
- `/help` - Show available commands
- `/online` - List currently connected users
- `/join <room>` - Join an existing room
- `/create <room>` - Create and join a room
- `/leave` - Leave the current room
- `/invite <username>` - Invite a user to your room
- `/kick <username>` - Kick a user from your room
- `/delete <room>` - Delete a room you own

### Friends
- `/friend <username>` - Send a friend request
- `/accept <username>` - Accept a pending friend request
- `/reject <username>` - Reject a pending friend request
- `/remove <username>` - Remove an existing friend
- `/friends` - List your friends and their status

### Messaging & Status
- `/msg <username> <message>` - Send a private message
- `/status <status>` - Update your presence status (ONLINE, OFFLINE, IN_ROOM, DO_NOT_DISTURB)

### Media & Files
- `/sendimage <path>` - Upload an image to the current room
- `/sendfile <path>` - Upload a file to the current room (chunked transfer)

### Session Management
- `/reconnect` - Reconnect using stored session token (after disconnect/reconnect)

### Control
- `/matchmake` - Enter matchmaking queue
- `/quit` - Disconnect from the server

## Packet Protocol

Convox uses length-prefixed JSON packets over TCP. Each packet consists of:

1. 4-byte big-endian payload length
2. JSON payload

Example message packet:
```json
{
  "type": "MESSAGE",
  "sender": "alice",
  "room": "global",
  "message": "Hello everyone!",
  "timestamp": "2026-06-12 12:00:00 UTC"
}
```

Supported packet types:

**Authentication**
- `LOGIN` - Initial user login
- `RECONNECT` - Reconnect with session token
- `SESSION_ACK` - Server confirms session or reconnect

**Messaging**
- `MESSAGE` - Room message broadcast
- `PRIVATE_MESSAGE` - Direct user-to-user message
- `ROOM_HISTORY` - Historical messages on room join

**Room Operations**
- `CREATE_ROOM`
- `JOIN_ROOM`
- `LEAVE_ROOM`
- `DELETE_ROOM`
- `INVITE_USER`
- `KICK_USER`

**Friends**
- `ADD_FRIEND`
- `ACCEPT_FRIEND`
- `REJECT_FRIEND`
- `REMOVE_FRIEND`
- `GET_FRIENDS`
- `FRIEND_REQUEST`
- `FRIEND_LIST`

**Media Transfer**
- `IMAGE` - Single image upload (PNG/JPG/JPEG, base64 encoded)
- `FILE` - File metadata and completion notification
- `FILE_START` - Begins chunked file transfer
- `FILE_CHUNK` - Single chunk in transfer
- `FILE_END` - Finalize chunked transfer
- `TRANSFER_PROGRESS` - Progress notification for active transfers

**Presence & Status**
- `GET_ONLINE_USERS` - List of connected users
- `STATUS_UPDATE` - Broadcast status change to friends
- `UPDATE_STATUS` - Request status change

**Scheduled Broadcasts**
- `SCHEDULE_BROADCAST` - Schedule a timed message

**System**
- `SYSTEM` - Server notifications
- `ERROR` - Error responses
- `MATCHMAKE` - Matchmaking queue request

## Example Packet Flows

### Image Transfer (Room)
```json
{"type":"IMAGE","sender":"alice","room":"global","filename":"photo.png","data":"iVBORw0K...","timestamp":"..."}
```

### File Transfer (Chunked)
1. Send FILE_START:
```json
{"type":"FILE_START","sender":"alice","target_room":"study","filename":"notes.pdf","filesize":204800,"transfer_id":"abc-123","total_chunks":7}
```
2. Send FILE_CHUNK x7:
```json
{"type":"FILE_CHUNK","sender":"alice","transfer_id":"abc-123","chunk_index":1,"data":"JVBERi..."}
```
3. Send FILE_END:
```json
{"type":"FILE_END","sender":"alice","transfer_id":"abc-123"}
```
4. Receive TRANSFER_PROGRESS:
```json
{"type":"TRANSFER_PROGRESS","transfer_id":"abc-123","progress":100,"received":7}
```

### Session Recovery
1. Initial login generates session token:
```json
{"type":"SESSION_ACK","session_token":"uuid-token","username":"alice","room":"global"}
```
2. After disconnect, client reconnects:
```json
{"type":"RECONNECT","session_token":"uuid-token"}
```
3. Server restores state:
```json
{"type":"SESSION_ACK","username":"alice","room":"global","session_token":"uuid-token"}
```

## Architecture Highlights

### Media Transfer Design
- **Chunking**: Large files split into 32KB chunks; configurable chunk size
- **Transfer State**: `ChunkManager` tracks in-flight transfers with unique IDs
- **Encoding**: Base64 encoding for JSON-compatible binary data
- **Storage**: Files organized by room/user under `storage/uploads/`
- **Persistence**: Transfer history and status stored in SQLite

### Session Recovery
- **Session Token**: UUID generated per login, stored in SQLite
- **State Restoration**: Username and room automatically restored on RECONNECT
- **Timeout**: Sessions expire after 15 minutes of inactivity
- **Clean Disconnect**: Session marked active/inactive on client disconnect

### Modular Layers
1. **Transport**: `protocol/packet.py` handles framing, `server/connection_manager.py` manages sockets
2. **Business Logic**: `server/service.py` routes packets to handlers
3. **Storage**: `database/db.py` SQLite wrapper, `storage/storage_manager.py` file system organization
4. **Domain Logic**: `rooms/`, `friends/`, `media/`, `scheduler/`, `presence/` handle specific features

## Storage Locations

- `storage/uploads/` - Uploaded images and files organized by room or user
- `storage/downloads/` - Client-side downloads directory
- `storage/temp/` - Temporary chunk buffers during transfer
- `database/convox.db` - SQLite database file

## Notes

- The SQLite database file is created under `database/convox.db` automatically.
- All file paths on clients and servers are platform-aware (Windows/Unix).
- Media transfers are atomic; failed transfers automatically clean up temporary chunks.
- Future phases will add voice streaming and screen sharing using similar media relay architecture.

## Setup

1. Install Python 3.10 or newer.
2. Open a terminal in the project root (`Progjar`).
3. (Optional) Create a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running Convox

Start the server:
```bash
python server.py
```

Start a client in another terminal:
```bash
python client.py
```

## Client Commands

- `/help` - Show available commands
- `/online` - List currently connected users
- `/join <room>` - Join an existing room
- `/create <room>` - Create and join a room
- `/leave` - Leave the current room
- `/invite <username>` - Invite a user to your room
- `/kick <username>` - Kick a user from your room
- `/delete <room>` - Delete a room you own
- `/matchmake` - Enter matchmaking queue
- `/friend <username>` - Send a friend request
- `/accept <username>` - Accept a pending friend request
- `/reject <username>` - Reject a pending friend request
- `/remove <username>` - Remove an existing friend
- `/friends` - List your friends and their status
- `/msg <username> <message>` - Send a private message
- `/status <status>` - Update your presence status
- `/quit` - Disconnect from the server

## Packet Protocol

Convox uses length-prefixed JSON packets over TCP. Each packet consists of:

1. 4-byte big-endian payload length
2. JSON payload

Example message packet:
```json
{
  "type": "MESSAGE",
  "sender": "alice",
  "room": "global",
  "message": "Hello everyone!",
  "timestamp": "2026-06-12 12:00:00 UTC"
}
```

Supported core packet types:

- `LOGIN`
- `MESSAGE`
- `PRIVATE_MESSAGE`
- `JOIN_ROOM`
- `LEAVE_ROOM`
- `CREATE_ROOM`
- `DELETE_ROOM`
- `INVITE_USER`
- `KICK_USER`
- `ADD_FRIEND`
- `ACCEPT_FRIEND`
- `REJECT_FRIEND`
- `REMOVE_FRIEND`
- `GET_FRIENDS`
- `FRIEND_REQUEST`
- `FRIEND_LIST`
- `GET_ONLINE_USERS`
- `STATUS_UPDATE`
- `UPDATE_STATUS`
- `MATCHMAKE`
- `SCHEDULE_BROADCAST`
- `ROOM_HISTORY`
- `SYSTEM`
- `ERROR`

## Example Packet Flow

1. Client connects and sends a login packet:
   ```json
   {"type":"LOGIN","sender":"alice"}
   ```
2. Server registers the user, generates session token, and broadcasts presence.
3. Alice uploads an image to global room:
   ```json
   {"type":"IMAGE","sender":"alice","room":"global","filename":"photo.png","data":"iVBORw0K...","timestamp":"..."}
   ```
4. Server stores and broadcasts to all room members.
5. Alice disconnects and later reconnects with her session token:
   ```json
   {"type":"RECONNECT","session_token":"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"}
   ```
6. Server restores her room state and confirms the reconnect.

## Notes

- The SQLite database file is created under `database/convox.db` automatically.
- The server and client are designed for future UI and media extensions while preserving terminal-based networking stability.
