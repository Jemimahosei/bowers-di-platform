# Bowers D&I Platform — single-container Docker build.
#
# Stage 1 builds the Next.js frontend to a static export (frontend/out).
# Stage 2 runs the FastAPI backend, which serves the API and the built
# frontend (SPA fallback) from the same process.
#
# The backend resolves the frontend at <project-root>/frontend/out, i.e.
# parents[2] of app/main.py. In this image the backend lives at /code, so
# the export is copied to /frontend/out to land at that path.

# ---- Stage 1: frontend ----
FROM node:20 AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci
COPY frontend/ ./frontend/
# NEXT_PUBLIC_API_URL defaults to "" (same-origin) for the single-container
# deploy: the frontend is served by the backend, so relative API calls work.
# Override at build time if the API lives elsewhere.
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN cd frontend && npm run build

# ---- Stage 2: backend ----
FROM python:3.12-slim
WORKDIR /code
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend-build /build/frontend/out /frontend/out
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
