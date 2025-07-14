# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables for better Python behavior in containers
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for health checks and HTTP transport
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN groupadd --gid 1001 mcp && \
    useradd --uid 1001 --gid mcp --shell /bin/bash --create-home mcp

# Set the working directory in the container
WORKDIR /usr/src/app

# Install the open-stocks-mcp package from PyPI
# Use the latest version with HTTP transport support
RUN pip install --no-cache-dir --upgrade open-stocks-mcp

# Verify that the package and its dependencies are installed correctly
RUN pip check && \
    pip show open-stocks-mcp

# Change ownership of the working directory to the mcp user
RUN chown -R mcp:mcp /usr/src/app

# Switch to the non-root user
USER mcp

# Add health check to monitor container status using HTTP endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

# Expose the HTTP transport port
EXPOSE 3001

# Default command runs the MCP server with HTTP transport
CMD ["open-stocks-mcp-server", "--transport", "http", "--host", "0.0.0.0", "--port", "3001"]
