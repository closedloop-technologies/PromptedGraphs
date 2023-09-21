ARG APP_NAME=quantready_api

# Base image
FROM python:3.10-slim-buster as staging

# Install necessary system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python - && chmod +x $POETRY_HOME/bin/poetry

# Set work directory
WORKDIR /app

# Copy only requirements to cache them in docker layer
COPY poetry.lock pyproject.toml /app/

# # Project initialization:
RUN poetry install --no-interaction --no-root

# # Copying the project files into the container
COPY . /app/

# # Install the project
RUN poetry install --no-interaction

# # Command to run tests
RUN poetry run pytest --cov quantready_api && poetry run coverage report

ENTRYPOINT [ "poetry", "run" ]
CMD [ "python", "-m", "quantready_api", "info" ]


FROM staging as build
ARG APP_NAME

WORKDIR /app
RUN poetry build --format wheel
RUN poetry export --format requirements.txt --output constraints.txt --without-hashes


FROM python:3.10-slim-buster as production
ARG APP_NAME

# Set environment variables
ENV \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

ENV \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Get build artifact wheel and install it respecting dependency versions
WORKDIR /app
COPY --from=build /app/dist/*.whl ./
COPY --from=build /app/constraints.txt ./
RUN pip install ./$APP_NAME*.whl --constraint constraints.txt
ENTRYPOINT [ "python"]
CMD [ "-m", "quantready_api", "info" ]
