FROM python:3.11-slim

# Use root from the start
USER root

# Update SO and install tools
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y \
        gcc \
        g++ \
        postgresql-client \
        unixodbc \
        unixodbc-dev \
        curl \
        gnupg2 \
        apt-transport-https \
        ca-certificates \
        iputils-ping \
        telnet \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry
RUN pip install poetry==1.7.1

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY . .

# Create user (optional, but we stay as root for debugging)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Expose port
EXPOSE 8000

# Default command
CMD ["poetry", "run", "uvicorn", "app.main:app","--host", "0.0.0.0","--port", "8000","--proxy-headers","--forwarded-allow-ips", "*"]
