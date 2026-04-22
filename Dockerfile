FROM dssat/dssat-csm:v4.8.2.0

RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    python3-venv \
    python3-poetry \
    python3-virtualenv \
    curl \
    gdal-bin=3.6.2+dfsg-1+b2 \
    libgdal-dev=3.6.2+dfsg-1+b2 \
    && rm -rf /var/lib/apt/lists/*

ENV GDAL_VERSION 3.6.2
ENV C_INCLUDE_PATH=/usr/include/python3.11/cpython
ENV CPLUS_INCLUDE_PATH=/usr/include/python3.11/cpython

WORKDIR /app/pythia

COPY pyproject.toml poetry.toml poetry.lock ./
RUN POETRY_VIRTUALENVS_CREATE=false poetry install --no-interaction --no-ansi

COPY . ./
ENV PATH="${PATH}:/app/pythia/bin"

ENTRYPOINT ["pythia"]
