# ARCHITECTURE.md

# Convox Architecture Documentation

## Overview

Convox is a modular realtime communication platform built using Python.
The system combines TCP-based messaging/control communication and UDP-based realtime voice streaming to create a scalable Discord-style communication platform.

Convox is designed with a modular client-server architecture to support:

* realtime chat
* matchmaking
* private/public rooms
* friend systems
* file & image transfer
* realtime voice communication
* reconnect/session recovery

The architecture emphasizes:

* modularity
* scalability
* separation of concerns
* networking stability
* extensibility for future features

---

# High-Level Architecture

```text
+---------------------------------------------------+
|                    GUI CLIENT                     |
|---------------------------------------------------|
| Chat UI | Friends | Rooms | Voice | Uploads      |
+---------------------------------------------------+
                    ↓
+---------------------------------------------------+
|                CLIENT CONTROLLERS                 |
|---------------------------------------------------|
| TCP Controller | UDP Voice Controller             |
+---------------------------------------------------+
                    ↓
        TCP Socket              UDP Socket
              ↓                      ↓

+---------------------------------------------------+
|                    SERVER CORE                    |
|---------------------------------------------------|
| Connection Manager | Service Router | Sessions    |
+---------------------------------------------------+
        ↓                ↓                ↓

+---------------------------------------------------+
|                APPLICATION MODULES                |
|---------------------------------------------------|
| Chat         | Rooms        | Matchmaking         |
| Friends      | Presence     | Scheduler           |
| Media        | Voice        | Logging             |
+---------------------------------------------------+
                    ↓
+---------------------------------------------------+
|                    DATABASE                       |
|---------------------------------------------------|
| SQLite Persistence Layer                          |
+---------------------------------------------------+
```

---

# Core Architectural Principles

## 1. Modular Monolith Architecture

Convox uses a modular monolith approach.

Each subsystem is isolated into independent modules:

* networking
* rooms
* matchmaking
* voice
* media transfer
* persistence
* GUI

Advantages:

* easier maintenance
* clear responsibility separation
* easier testing
* scalable codebase
* simpler deployment than microservices

---

## 2. TCP / UDP Separation

Convox separates communication based on reliability requirements.

### TCP Responsibilities

Used for:

* login
* authentication
* messaging
* room control
* matchmaking
* file transfer control
* friend system
* scheduled broadcasts

Reason:
TCP guarantees:

* ordered delivery
* reliable transfer
* retransmission

---

### UDP Responsibilities

Used for:

* realtime voice communication

Reason:
UDP provides:

* low latency
* lightweight packets
* better realtime responsiveness

Voice packets are intentionally non-persistent.

---

# Project Structure

```text
convox/
│
├── client/
├── server/
├── voice/
├── gui/
├── database/
├── protocol/
├── media/
├── matchmaking/
├── rooms/
├── friends/
├── scheduler/
├── presence/
├── logging/
├── storage/
└── utils/
```

---

# Networking Architecture

## TCP Layer

The TCP layer handles:

* client connections
* packet routing
* room messaging
* matchmaking
* friend requests
* persistence operations

Core files:

```text
server/
 ├── server.py
 ├── service.py
 ├── connection_manager.py
```

---

## UDP Voice Layer

The UDP layer handles:

* voice frame streaming
* realtime voice relay
* jitter buffering
* active speaker tracking

Core files:

```text
voice/
 ├── udp_server.py
 ├── udp_client.py
 ├── voice_room.py
 ├── jitter_buffer.py
```

---

# Packet Protocol System

Convox uses a JSON-based packet protocol.

## Packet Structure

Example:

```json
{
  "type": "MESSAGE",
  "sender": "fabian",
  "room": "global",
  "message": "hello"
}
```

---

## Packet Categories

### Authentication

* LOGIN
* RECONNECT
* SESSION_ACK

### Messaging

* MESSAGE
* PRIVATE_MESSAGE
* ROOM_HISTORY

### Room Management

* CREATE_ROOM
* JOIN_ROOM
* LEAVE_ROOM
* DELETE_ROOM

### Matchmaking

* MATCHMAKE
* MATCH_FOUND

### Friend System

* ADD_FRIEND
* ACCEPT_FRIEND
* REJECT_FRIEND

### Media Transfer

* IMAGE
* FILE_START
* FILE_CHUNK
* FILE_END

### Voice System

* VOICE_START
* VOICE_STOP
* VOICE_STATUS
* VOICE_FRAME

---

# Session Recovery System

Convox supports reconnect recovery.

## Session Flow

```text
LOGIN
↓
Generate session token
↓
Store session state
↓
Disconnect detected
↓
Client reconnects
↓
RECONNECT packet
↓
Restore room + status
```

Stored session data:

* username
* active room
* presence state
* voice state

---

# Room System

The room architecture supports:

* global rooms
* private rooms
* matchmaking rooms
* invite-only rooms

## Room Features

* owner permissions
* capacity limits
* password protection
* automatic cleanup

Room management handled by:

```text
rooms/
 ├── room_manager.py
 └── permissions.py
```

---

# Matchmaking System

The matchmaking subsystem:

* stores queue state
* matches compatible users
* auto-generates rooms

Flow:

```text
User joins queue
↓
Queue manager searches match
↓
Room generated
↓
Users auto-joined
```

Core files:

```text
matchmaking/
 ├── matcher.py
 ├── queue_manager.py
 └── room_generator.py
```

---

# Media Transfer Architecture

Convox supports:

* image transfer
* generic file transfer
* chunked uploads

Large files use chunk-based transfer:

```text
FILE_START
↓
FILE_CHUNK
↓
FILE_CHUNK
↓
FILE_END
```

Advantages:

* avoids oversized packets
* supports progress tracking
* safer memory handling

Core files:

```text
media/
 ├── image_transfer.py
 ├── chunk_manager.py
 ├── storage_manager.py
 └── encoder.py
```

---

# Voice Communication Architecture

The voice subsystem is designed as a lightweight realtime relay system.

## Voice Flow

```text
Microphone Capture
↓
PCM Audio Frame
↓
UDP Packet
↓
Voice Server
↓
Relay to Participants
↓
Audio Playback
```

Features:

* push-to-talk
* mute/unmute
* speaking indicators
* jitter buffering

Voice packets are:

* non-persistent
* low-latency
* room-scoped

---

# GUI Architecture

Convox uses PyQt6 for the desktop GUI layer.

The GUI is intentionally separated from business logic.

## GUI Flow

```text
GUI Widget
↓
Controller
↓
Packet Builder
↓
TCP/UDP Controller
↓
Server
```

The GUI never directly handles:

* database logic
* room logic
* socket parsing

This separation improves:

* maintainability
* scalability
* testing

---

# Database Architecture

SQLite is used for persistence.

Stored data:

* users
* friends
* messages
* rooms
* room members
* broadcasts
* file transfers
* sessions

Database access is centralized.

Core files:

```text
database/
 ├── db.py
 ├── models.py
 └── queries.py
```

---

# Concurrency Model

Convox uses:

* threading
* asynchronous event handling
* non-blocking socket communication

Important principles:

* GUI thread never blocks
* voice relay is lightweight
* packet routing isolated from rendering

---

# Logging System

The logging subsystem records:

* login/logout
* room activity
* matchmaking events
* media transfers
* voice events
* server errors

Purpose:

* debugging
* monitoring
* stability tracking

---

# Security Considerations

Current MVP protections:

* duplicate login prevention
* malformed packet validation
* room permission checks
* transfer size limits
* chunk validation

Not yet implemented:

* encryption
* authentication tokens
* advanced access control

---

# Current Development Status

## Completed

* TCP networking
* UDP voice streaming
* matchmaking
* room system
* friend system
* file/image transfer
* reconnect recovery
* persistence
* modular GUI architecture

## Planned / Future

* GUI polishing
* advanced voice codec
* stress testing
* optimization
* optional screen sharing

---

# Design Philosophy

Convox prioritizes:

1. networking stability
2. modular architecture
3. realtime responsiveness
4. scalability
5. maintainability

The system is intentionally designed to resemble the architecture of modern realtime communication platforms while remaining realistic for an academic networking project.

---

# Final Notes

Convox is not designed as a simple chat application.

It is designed as:

* a modular realtime communication platform,
* a networking systems project,
* and a scalable software engineering architecture prototype.

The project demonstrates:

* TCP/UDP communication
* realtime media systems
* modular backend architecture
* persistence management
* session recovery
* concurrent networking systems
* modern GUI integration
