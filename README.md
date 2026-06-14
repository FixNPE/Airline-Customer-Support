# Airline Customer Support API

An AI-powered FastAPI application for handling airline customer support queries.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **GitHub Codespaces Ready**: Fully configured for development in Codespaces
- **CORS Enabled**: Supports cross-origin requests for frontend integration
- **Batch Processing**: Handle multiple queries efficiently
- **Health Checks**: Built-in endpoints for monitoring
- **Swagger Documentation**: Auto-generated API documentation at `/docs`
- **Flexible Backend Integration**: Easy to connect your AI workflow

## Quick Start

### In GitHub Codespaces

1. **Create a Codespace**:
   - Click "Code" → "Codespaces" → "Create codespace on main"
   - Wait for the environment to set up

2. **Start the API**:
   ```bash
   python main.py
   ```
   Or use uvicorn directly:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0
   ```

3. **Access the API**:
   - API Docs: `https://<codespace-url>:8000/docs`
   - Health Check: `https://<codespace-url>:8000/health`
   - API Base: `https://<codespace-url>:8000`

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run the server**:
   ```bash
   python main.py
   ```

4. **Access documentation**:
   - Open http://localhost:8000/docs in your browser

## API Endpoints

### POST /support/query
Process a single customer support query.

**Request**:
```json
{
  "query": "How do I change my flight date?",
  "customer_id": "CUST123",
  "context": {
    "booking_id": "BK12345",
    "previous_queries": []
  }
}
```

**Response**:
```json
{
  "response": "You can change your flight date through our website...",
  "status": "success",
  "customer_id": "CUST123",
  "suggested_actions": ["View booking", "Change date"],
  "confidence_score": 0.95
}
```

### POST /support/batch
Process multiple support queries.

**Request**:
```json
[
  {"query": "How do I check in?", "customer_id": "CUST123"},
  {"query": "What's my refund status?", "customer_id": "CUST124"}
]
```

### GET /health
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "backend": "available"
}
```

## Integration with Your Backend

To connect your AI support workflow:

1. **Update the import** in `main.py`:
   ```python
   from your_module import process_customer_support_query
   ```

2. **Ensure your function signature matches**:
   ```python
   async def process_customer_support_query(
       query: str,
       customer_id: Optional[str] = None,
       context: Optional[dict] = None
   ) -> dict:
       # Your implementation
       return {
           "response": "...",
           "status": "success",
           "suggested_actions": [...],
           "confidence_score": 0.95
       }
   ```

## Testing the API

### Using curl
```bash
curl -X POST "http://localhost:8000/support/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I book a flight?"}'
```

### Using Python requests
```python
import requests

response = requests.post(
    "http://localhost:8000/support/query",
    json={"query": "What are your baggage policies?"}
)
print(response.json())
```

### Using REST Client (VS Code)
Create a `requests.http` file:
```
POST http://localhost:8000/support/query
Content-Type: application/json

{
  "query": "How do I change my booking?",
  "customer_id": "CUST123"
}
```

## Production Deployment

### Environment variables to set:
```bash
ENVIRONMENT=production
PORT=8000
API_KEY=your_secure_api_key
```

### Using Gunicorn (recommended):
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Docker deployment:
Create a `Dockerfile` for containerized deployment.

## Architecture

```
┌─────────────────────────┐
│   Client/UI             │
└──────────────┬──────────┘
               │ HTTP
               ▼
┌─────────────────────────┐
│   FastAPI App           │
│  (main.py)              │
└──────────────┬──────────┘
               │
               ▼
┌─────────────────────────┐
│  Backend Function       │
│ (AI Workflow)           │
└─────────────────────────┘
```

## Development Tips

- **Auto-reload**: Use `--reload` flag during development
- **Debug mode**: Access interactive API docs at `/docs`
- **Request logging**: Check console output for detailed logs
- **CORS issues**: Verify origin URLs in the middleware configuration

## Troubleshooting

### Port already in use
```bash
lsof -i :8000
kill -9 <PID>
```

### Import errors
- Ensure `requirements.txt` packages are installed
- Check Python path and virtual environment
- Verify module imports in `main.py`

### Backend not connecting
- Check the backend URL in `.env`
- Verify backend service is running
- Review error logs in console

## Contributing

1. Create a branch for your feature
2. Make changes and test locally
3. Submit a pull request with description

## License

MIT
