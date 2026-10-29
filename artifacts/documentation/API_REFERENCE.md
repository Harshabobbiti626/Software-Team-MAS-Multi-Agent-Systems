# API & SDK Reference: Integration Test Service

## Endpoint: `POST /api/v1/resource`
Creates a new resource managed under Integration Test Service.

### Runnable Example
```bash
curl -X POST http://localhost:8080/api/v1/resource \
  -H "Content-Type: application/json" \
  -d '{"name": "Widget-Enterprise", "category": "Core"}'
```

### Response (201 Created)
```json
{
  "id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
  "name": "Widget-Enterprise",
  "status": "ACTIVE"
}
```
