FROM dssat-pythia-base

COPY . /app/pythia

RUN echo "#!/bin/bash" > /app/pythia.sh && \
echo "" >> /app/pythia.sh && \
echo "source /usr/local/miniconda/etc/profile.d/conda.sh" >> /app/pythia.sh && \
echo "conda activate pythia" >> /app/pythia.sh && \
echo "python /app/pythia/pythia.py \$@" >> /app/pythia.sh && \
chmod 755 /app/pythia.sh

ENTRYPOINT ["/app/pythia.sh"]
CMD ["-h"]