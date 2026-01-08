# agent-team API

This API runs in **single-user mode** and uses an **in-memory store** (no database, no login). Data resets when the server restarts.

## Base URL

```
http://localhost:8080/api
```

## Agents

- `GET /agents`
- `POST /agents`
- `GET /agents/{id}`
- `PUT /agents/{id}`
- `DELETE /agents/{id}`
- `POST /agents/{id}/duplicate`
- `GET /agents/templates`
- `POST /agents/from-template`

## Teams

- `GET /teams`
- `POST /teams`
- `GET /teams/{id}`
- `PUT /teams/{id}`
- `DELETE /teams/{id}`
- `POST /teams/{id}/duplicate`
- `POST /teams/{id}/members`
- `DELETE /teams/{id}/members/{agent_id}`
- `POST /teams/{id}/members/reorder`

## Executions

- `GET /executions`
- `POST /executions`
- `GET /executions/{id}`
- `GET /executions/{id}/messages`
- `POST /executions/{id}/control`
- `DELETE /executions/{id}`

### WebSocket

- `WS /executions/{id}/ws`

#### Client messages

- Start (optional): `{"type":"start"}`
- Follow-up: `{"type":"followup","input":"...","target_agent_id":null}`
- Control: `{"type":"control","action":"pause|resume|stop","params":{}}`
- Ping: `{"type":"ping"}`

#### Server events

- `connected` (data: execution_id)
- `user` (data: content, round, message_id, message_sequence)
- `opinion` (data: content, agent_name, round, phase, message_id, message_sequence)
- `status` (data: status or message)
- `error` (data: message)
## Model Configs

- `GET /models`
- `POST /models`
- `GET /models/{id}`
- `PUT /models/{id}`
- `DELETE /models/{id}`
- `POST /models/{id}/test`
