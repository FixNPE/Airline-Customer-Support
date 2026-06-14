# Streamlit UI Deployment Guide

This guide provides step-by-step instructions for deploying and running the Streamlit-based airline customer support UI in GitHub Codespaces.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Running Both Backend and Frontend](#running-both-backend-and-frontend)
4. [Using Streamlit Secrets](#using-streamlit-secrets)
5. [Deployment Options](#deployment-options)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

- GitHub Codespaces environment (or local Python 3.8+)
- Python pip package manager
- FastAPI backend running (see README.md)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- **FastAPI** and **Uvicorn** - Backend API framework
- **Streamlit** - Frontend UI framework
- **Pydantic** - Data validation
- **Requests** - HTTP client for backend communication
- **python-dotenv** - Environment variable management

### 2. Start the FastAPI Backend

Open a terminal in GitHub Codespaces:

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. Start the Streamlit Frontend

Open a **second terminal** in GitHub Codespaces:

```bash
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

You should see output like:
```
  You can now view your Streamlit app in your browser.

  URL: http://localhost:8501
```

## Running Both Backend and Frontend

### Using GitHub Codespaces Ports

1. **Terminal 1 - Backend API**
   ```bash
   python main.py
   ```
   - Runs on `http://localhost:8000` (or your Codespace URL with port 8000)

2. **Terminal 2 - Frontend UI**
   ```bash
   streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
   ```
   - Runs on `http://localhost:8501` (or your Codespace URL with port 8501)

### Accessing via Codespaces

GitHub Codespaces will automatically create public URLs for your ports:
- **Backend**: `https://<your-codespace-name>-8000.preview.app.github.dev`
- **Frontend**: `https://<your-codespace-name>-8501.preview.app.github.dev`

The Streamlit UI will automatically connect to the backend if running on the same machine.

## Using Streamlit Secrets

For production deployments, you can configure the backend API URL using Streamlit secrets:

### Local Development with `.streamlit/secrets.toml`

1. Create `.streamlit/secrets.toml` in your project:
   ```bash
   mkdir -p .streamlit
   ```

2. Add your API configuration:
   ```toml
   api_base_url = "http://localhost:8000"
   ```

3. For Codespaces or remote deployments:
   ```toml
   api_base_url = "https://<your-codespace-name>-8000.preview.app.github.dev"
   ```

### Streamlit Cloud Deployment

If deploying to Streamlit Cloud:

1. Go to [Streamlit Cloud](https://share.streamlit.io/)
2. Connect your GitHub repository
3. In the app settings, add secrets under "Advanced settings":
   ```toml
   api_base_url = "https://your-backend-url.com"
   ```

## Deployment Options

### Option 1: GitHub Codespaces (Recommended for Development)

**Pros:**
- No local setup required
- Free tier available
- Integrated with GitHub
- Automatic port forwarding

**Steps:**
1. Open repository in Codespaces
2. Follow "Quick Start" section above
3. Access via public Codespace URLs

### Option 2: Local Development

**Pros:**
- Full control
- Faster development cycle
- Can test offline

**Steps:**
1. Clone repository: `git clone <repo-url>`
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Follow "Quick Start" section

### Option 3: Docker Deployment

**Pros:**
- Consistent environment
- Easy to scale
- Cloud-ready

**Dockerfile example:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000 8501

# Start both services
CMD sh -c 'python main.py & streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0'
```

Build and run:
```bash
docker build -t airline-support .
docker run -p 8000:8000 -p 8501:8501 airline-support
```

### Option 4: Streamlit Cloud + External Backend

**For frontend only:**
1. Push repository to GitHub
2. Go to [Streamlit Cloud](https://share.streamlit.io/)
3. Deploy "streamlit_app.py"
4. Configure backend URL in secrets

## Configuration

### Environment Variables

Create a `.env` file for local configuration:

```bash
# Backend Configuration
PORT=8000
ENVIRONMENT=development

# API Configuration
API_KEY=your_api_key_here
```

### Streamlit Configuration

Create `.streamlit/config.toml` for Streamlit settings:

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"

[client]
showErrorDetails = true

[server]
headless = true
maxUploadSize = 200
```

## Performance Optimization

### Caching Responses

The Streamlit app uses session state for conversation history. For additional caching:

```python
@st.cache_data
def get_health_status(api_url: str):
    # Cached health check
    return client.health_check()
```

### Async Processing

For large batch queries, consider using async endpoints:

```bash
streamlit run streamlit_app.py --logger.level=debug
```

## Troubleshooting

### Streamlit Won't Start

**Problem:** `Permission denied` or `Port already in use`

**Solution:**
```bash
# Check if port 8501 is in use
lsof -i :8501

# Kill the process
kill -9 <PID>

# Or use a different port
streamlit run streamlit_app.py --server.port 8502
```

### Backend Connection Error

**Problem:** `❌ Backend Offline` message in UI

**Solution:**
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check the API URL in the Streamlit sidebar
3. For Codespaces, use the full URL: `https://<codespace>-8000.preview.app.github.dev`
4. Verify CORS is enabled in `main.py`

### Slow Response Times

**Problem:** Queries take too long

**Solution:**
1. Check backend performance: `curl -X POST http://localhost:8000/support/query -H "Content-Type: application/json" -d '{"query": "test"}'`
2. Monitor system resources: `top` or `htop`
3. Check network latency for remote deployments

### Session State Not Persisting

**Problem:** Conversation history disappears on refresh

**Solution:**
This is expected behavior - Streamlit clears session state on rerun. To persist data:

```python
# Add to streamlit_app.py
import pickle

# Save history
with open('history.pkl', 'wb') as f:
    pickle.dump(st.session_state.conversation_history, f)

# Load history
if os.path.exists('history.pkl'):
    with open('history.pkl', 'rb') as f:
        st.session_state.conversation_history = pickle.load(f)
```

### CORS Errors

**Problem:** `CORS error` in browser console

**Solution:**
Update CORS in `main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "https://<your-domain>"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Monitoring and Logging

### Enable Debug Logging

```bash
streamlit run streamlit_app.py --logger.level=debug
```

### View Backend Logs

```bash
uvicorn main:app --reload --log-level debug
```

### Monitor API Health

Create a monitoring script:

```python
import requests
import time

while True:
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        print(f"✅ Backend healthy: {response.json()}")
    except Exception as e:
        print(f"❌ Backend error: {e}")
    
    time.sleep(30)
```

## Next Steps

1. **Test the Interface**: Try different query types and batch processing
2. **Customize Styling**: Edit CSS in `streamlit_app.py` to match your branding
3. **Add Authentication**: Implement user login if needed
4. **Scale the Backend**: Use a production ASGI server like Gunicorn
5. **Monitor Performance**: Set up logging and metrics collection

## Support and Issues

For issues or questions:
1. Check the [Streamlit Documentation](https://docs.streamlit.io/)
2. Review [FastAPI Documentation](https://fastapi.tiangolo.com/)
3. Check GitHub Issues in the repository
4. Create a new issue with detailed error logs

---

**Last Updated:** 2026-06-14  
**Streamlit Version:** 1.28.1  
**FastAPI Version:** 0.104.1
