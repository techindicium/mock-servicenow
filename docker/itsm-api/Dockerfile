FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY static/ ./static/

ENV PORT=8030
ENV DATABASE_PATH=/data/mock_servicenow.db

EXPOSE 8030

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python3 -c "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT', '8030') + '/', timeout=2)"

# The seed command is documented as a separate, explicitly-invoked step (never wired into
# app/main.py's own startup — see fixture-seeding.spec.md's Preconditions), so it is invoked
# here as its own command before uvicorn starts, not folded into the ASGI app's lifecycle.
# It is idempotent, so this is safe on every container start/restart, not just the first.
CMD ["sh", "-c", "python3 -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
