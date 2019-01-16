FROM python:3.6
RUN apt-get update && \
    apt-get install libgdal-dev gdal-bin -y --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    pip install numpy && \
    pip install rasterio && \
    pip install pandas
COPY pythia.py /run/pythia.py
WORKDIR /data
ENTRYPOINT ["python", "/run/pythia.py"]
CMD ["-h"]
