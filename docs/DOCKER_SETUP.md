# Docker Setup Guide

## Overview

This project is containerized using Docker for local development and eventual deployment. The backend runs FastAPI in a Docker container with support for macOS, Linux, and Windows.

## Prerequisites

- Docker Desktop installed (https://www.docker.com/products/docker-desktop)
- For Windows: PowerShell with execution policy allowing scripts

## Quick Start

### macOS/Linux

```bash
cd /Users/vinodiyer/Projects/pm
chmod +x scripts/start.sh scripts/stop.sh
./scripts/start.sh
```

### Windows

```powershell
cd pm
.\scripts\start.ps1
```

## Testing

Once the service is running:

```bash
# Health check
curl http://localhost:8000/health

# Test API endpoint
curl http://localhost:8000/api/test

# Frontend (hello-world HTML)
open http://localhost:8000
# or visit http://localhost:8000 in your browser
```

Expected responses:

- **Health:** `{"status":"ok"}`
- **API Test:** `{"message":"Hello from FastAPI!","value":42}`
- **Frontend:** Hello World HTML page

## Stopping the Service

### macOS/Linux

```bash
./scripts/stop.sh
```

### Windows

```powershell
.\scripts\stop.ps1
```

## Project Structure

```
pm/
├── Dockerfile           # Container definition
├── docker-compose.yml   # Service orchestration
├── backend/
│   ├── app/
│   │   ├── main.py      # FastAPI entry point
│   │   └── __init__.py
│   ├── requirements.txt  # Python dependencies
│   └── pyproject.toml    # Project metadata
├── scripts/
│   ├── start.sh         # Start script (macOS/Linux)
│   ├── stop.sh          # Stop script (macOS/Linux)
│   ├── start.ps1        # Start script (Windows)
│   └── stop.ps1         # Stop script (Windows)
├── static/
│   └── index.html       # Static hello-world page
└── frontend/            # Next.js frontend (to be integrated)
```

## Environment Variables

The `.env` file in the project root is loaded by Docker. Currently used for:

- `OPENROUTER_API_KEY` - AI API key (for Part 8+)

Create `.env` file if it doesn't exist:

```
OPENROUTER_API_KEY=your-key-here
```

## Development Workflow

### Local Changes

The `docker-compose.yml` mounts volumes for live code reloading:

- Backend code: `./backend/app` → `/app/app`
- Static files: `./static` → `/app/static`

Edit backend code locally, and the container will automatically reload.

### Rebuilding After Dependency Changes

If you modify `requirements.txt` or `pyproject.toml`:

```bash
docker-compose build --no-cache
docker-compose up -d
```

Or use the start script which rebuilds automatically:

```bash
./scripts/start.sh
```

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:

```bash
# Kill existing Docker containers
docker kill $(docker ps -q)

# Or modify docker-compose.yml to use a different port:
# ports:
#   - "8001:8000"
```

### Permission Denied (macOS/Linux)

```bash
chmod +x scripts/start.sh scripts/stop.sh
```

### Docker Daemon Not Running

- macOS/Linux: Start Docker Desktop or `docker daemon`
- Windows: Start Docker Desktop from Start Menu

### Container Not Starting

Check logs:

```bash
docker-compose logs
```

## Next Steps

- **Part 3:** Integrate Next.js frontend static build
- **Part 4:** Add authentication system
- **Part 5:** Design database schema
