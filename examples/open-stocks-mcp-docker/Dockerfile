FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1001 mcp && \
    useradd --uid 1001 --gid mcp --shell /bin/bash --create-home mcp

WORKDIR /usr/src/app

ARG OPEN_STOCKS_MCP_VERSION=0.6.5
RUN pip install --no-cache-dir --upgrade open-stocks-mcp==${OPEN_STOCKS_MCP_VERSION}

RUN pip check && \
    pip show open-stocks-mcp

RUN chown -R mcp:mcp /usr/src/app

RUN install -d -m 700 -o mcp -g mcp /home/mcp/.tokens

USER mcp

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

EXPOSE 3001

CMD ["open-stocks-mcp-server", "--transport", "http", "--host", "0.0.0.0", "--port", "3001"]
