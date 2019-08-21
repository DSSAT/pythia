FROM debian:stable-slim

COPY . /app/pythia

RUN ln -sf /bin/bash /bin/sh && \
apt-get update && \
apt-get install ca-certificates python3 wget gfortran cmake -y --no-install-recommends &&\
apt-get clean && rm -rf /var/lib/apt/lists/* && \
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
bash Miniconda3-latest-Linux-x86_64.sh -b -p /usr/local/miniconda && \
. /usr/local/miniconda/bin/activate &&\
conda init && \
conda update -y conda && \
conda env create -f /app/pythia/environment.yml && \
echo "#!/bin/bash" > /app/pythia.sh && \
echo "" >> /app/pythia.sh && \
echo "source /usr/local/miniconda/etc/profile.d/conda.sh" >> /app/pythia.sh && \
echo "conda activate pythia" >> /app/pythia.sh && \
echo "python /app/pythia/pythia.py \$@" >> /app/pythia.sh && \
chmod 755 /app/pythia.sh

ENTRYPOINT ["/app/pythia.sh"]
CMD ["-h"]
#ENTRYPOINT ["/bin/bash"]
