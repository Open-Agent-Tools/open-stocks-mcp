# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install the open-stocks-mcp package from PyPI
# This creates a base image with the library and its dependencies installed.
RUN pip install --no-cache-dir open-stocks-mcp

# Verify that the package and its dependencies are installed correctly
RUN pip check
RUN pip show open-stocks-mcp

# No CMD or ENTRYPOINT is defined.
# This image can be used as a base for other images or for interactive sessions.
