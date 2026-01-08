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
- `GET /executions/{id}/stream` (SSE)
- `POST /executions/{id}/control`
- `POST /executions/{id}/followup` (SSE)
- `DELETE /executions/{id}`

## Model Configs

- `GET /models`
- `POST /models`
- `GET /models/{id}`
- `PUT /models/{id}`
- `DELETE /models/{id}`
- `POST /models/{id}/test`
