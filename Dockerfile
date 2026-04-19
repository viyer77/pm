FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
# Clean old builds and rebuild
RUN rm -rf .next out dist && npm run build

FROM python:3.12-slim

WORKDIR /app

# Install uv package manager
RUN pip install uv

# Copy backend dependencies
COPY backend/pyproject.toml backend/requirements.txt ./

# Install dependencies with uv
RUN uv pip install --system -r requirements.txt

# Copy backend code
COPY backend/app ./app

# Create static directory
RUN mkdir -p /app/static

# Copy built frontend from builder stage
COPY --from=frontend-builder /frontend/out /app/static

# Copy .env for API keys if it exists
# Create empty .env if not provided
RUN touch /app/.env

# Expose port
EXPOSE 8000

# Run FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
