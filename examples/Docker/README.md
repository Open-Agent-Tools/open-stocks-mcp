# Docker Example for Open Stocks MCP

This directory contains a working example of how to run the Open Stocks MCP server using Docker and Docker Compose.

This setup uses a two-stage approach:
1.  A `Dockerfile` that creates a base image with the `open-stocks-mcp` library installed and verified.
2.  A `docker-compose.yml` file that runs the server using the base image and injects your credentials at runtime.

## Prerequisites

- [Docker](httpss://docs.docker.com/get-docker/)
- [Docker Compose](httpss://docs.docker.com/compose/install/)

## Setup

### 1. Build the Base Image

First, build the base image that contains the verified library installation.

```bash
docker build . -t open-stocks-mcp-base:latest
```

### 2. Create an Environment File

You need to provide your Robinhood credentials to the server.

1.  Create a file named `.env` in this directory (`examples/Docker`).
2.  Add your credentials to the file like this:

    ```env
    # .env
    ROBINHOOD_USERNAME=your_robinhood_username
    ROBINHOOD_PASSWORD=your_robinhood_password
    ```

### 3. Run the Server

With the base image built and the `.env` file in place, you can start the server using Docker Compose.

```bash
docker-compose up
```

You can add the `-d` flag (`docker-compose up -d`) to run the container in detached mode.

### 4. Accessing the Server

The MCP server will be running and accessible via Server-Sent Events (SSE) on port `3001`. You can connect with any MCP client, such as `mcp-cli`:

```bash
mcp-cli --url http://localhost:3001
```

### 5. Stopping the Server

To stop the server, press `Ctrl+C` in the terminal where `docker-compose up` is running, or use `docker-compose down` if running in detached mode.
