FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_server/ ./mcp_server/

ENV PORT=8031
ENV API_BASE_URL=http://itsm-api:8030

EXPOSE 8031

CMD ["python3", "-m", "mcp_server.server"]
