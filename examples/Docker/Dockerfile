# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables for better Python behavior in containers
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create a non-root user for security
RUN groupadd --gid 1001 mcp && \
    useradd --uid 1001 --gid mcp --shell /bin/bash --create-home mcp

# Set the working directory in the container
WORKDIR /usr/src/app

# Install the open-stocks-mcp package from PyPI
# Use the latest version and install without cache to reduce image size
RUN pip install --no-cache-dir open-stocks-mcp==0.1.5

# Verify that the package and its dependencies are installed correctly
RUN pip check && \
    pip show open-stocks-mcp

# Change ownership of the working directory to the mcp user
RUN chown -R mcp:mcp /usr/src/app

# Switch to the non-root user
USER mcp

# Add health check to monitor container status
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import open_stocks_mcp; print('OK')" || exit 1

# Expose the default MCP server port
EXPOSE 3001

# Default command runs the MCP server with SSE transport
CMD ["open-stocks-mcp-server", "--transport", "sse", "--port", "3001"]
