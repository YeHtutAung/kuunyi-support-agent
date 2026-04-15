FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the packages ADK and the agent need
COPY kuunyi_admin_agent/ ./kuunyi_admin_agent/
COPY my_support_agent/ ./my_support_agent/

EXPOSE 8000

CMD ["adk", "api_server", "--host", "0.0.0.0", "--port", "8000"]
