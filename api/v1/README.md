# Hockey-Blast REST API – v1

This document explains how to call the **v1** REST endpoints that are exposed through the `rest_api` blueprint (mounted in `blueprints/rest_api.py`) and protected by a simple **API-key** scheme.

---

## Authentication – API Key

| Property | Value |
|----------|-------|
| Header name | `X-API-KEY` |
| Type | `apiKey` (sent in `header`) |
| Where is the valid key stored? | • `API_KEY` environment variable<br>• or `app.config['API_KEY']` |

**How it works**

1. Every request handled by the REST API passes through the `require_api_key` decorator.
2. The decorator compares the value of the `X-API-KEY` header with the expected key loaded at application start-up.
3. If the header is missing or the value does not match, the server responds with **HTTP 401 Unauthorized**.

**Setting the key**

```bash
# .env (recommended – never commit to VCS)
API_KEY=my-super-secret-key
```

or

```python
# During app/bootstrap code
app.config['API_KEY'] = 'my-super-secret-key'
```
