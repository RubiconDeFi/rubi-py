FROM python:3.10-slim-buster

# https://stackoverflow.com/questions/59812009/what-is-the-use-of-pythonunbuffered-in-docker-file
ENV PYTHONUNBUFFERED=1 \
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_CACHE_DIR='/var/cache/pypoetry'

# Get build wheels for ciso8601
RUN apt-get update && apt-get upgrade -y \
    && apt-get install --no-install-recommends -y build-essential \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

RUN pip install "poetry==1.2.2"

# Copy only requirements to cache them in docker layer
WORKDIR /bot
COPY poetry.lock pyproject.toml /bot/

# MASSIVE HACK TO REMOVE DEV DEPENDENCIES BEFORE INSTALL
RUN sed -i -n '/tool.poetry.dev-dependencies/q;p' pyproject.toml

# Clean up by removing poetry
RUN pip uninstall poetry -y

# Creating folders, and files for a project:
COPY . /bot

# Run the image as a non-root user
RUN adduser -D bot
USER bot

ENTRYPOINT ["python", "main.py"]
