FROM dssat/dssat-csm:v4.8.2.0

# The DSSAT 4.8.2 image is Debian 12, but its APT sources use the floating
# "stable" suite. Pin the suite to bookworm so a future Debian release cannot
# mix packages from a different operating-system version into this image.
RUN sed -i \
      -e 's/Suites: stable stable-updates/Suites: bookworm bookworm-updates/' \
      -e 's/Suites: stable-security/Suites: bookworm-security/' \
      /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      python3 \
      python3-dev \
      python3-venv \
      curl \
      gdal-bin \
      libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV="/opt/pythia-venv" \
    PATH="/opt/pythia-venv/bin:${PATH}" \
    PIP_NO_CACHE_DIR=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Install Poetry in an isolated environment instead of depending on the
# distribution's Poetry package or modifying Debian's managed Python.
RUN python3 -m venv /opt/pythia-venv \
    && python -m pip install --upgrade pip \
    && python -m pip install "poetry>=1.8,<3"

WORKDIR /app/pythia

# Cache third-party dependencies separately from the application source.
COPY pyproject.toml poetry.toml poetry.lock ./
RUN poetry install --only main --no-root --no-ansi

COPY . ./
RUN poetry install --only main --no-ansi

ENV PATH="${PATH}:/app/pythia/bin"

ENTRYPOINT ["pythia"]
