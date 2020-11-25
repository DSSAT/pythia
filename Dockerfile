FROM dssat/dssat-csm

COPY . /app/pythia
RUN ln -sf /bin/bash /bin/sh && \
# install pre-reqs for pyenv installed pythons
apt-get install -y build-essential libssl-dev zlib1g-dev libbz2-dev \
libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
xz-utils tk-dev libffi-dev liblzma-dev python-openssl git libspatialindex-dev && \
# setup pyenv
curl https://pyenv.run | bash && \                          
echo 'export PATH="/root/.pyenv/bin:/root/.local/bin:$PATH"' >> ~/.bashrc && \
echo 'eval "$(pyenv init -)"' >> ~/.bashrc && \
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc && \
export PATH="/root/.pyenv/bin:/root/.local/bin:$PATH" && \
eval "$(pyenv init -)" && \
eval "$(pyenv virtualenv-init i)" && \
# install python 3.7.9
pyenv install 3.7.9 && \
pyenv rehash && \
pyenv virtualenv 3.7.9 pythia-3.7.9 && \
pyenv activate pythia-3.7.9 && \
pip install --upgrade pip && \
pip install pipenv && \
# install dependencies
cd /app/pythia && \
pipenv install && \
echo "#!/bin/bash" > /app/pythia.sh && \
echo "" >> /app/pythia.sh && \
echo 'export PATH="/root/.pyenv/bin:/root/.local/bin:$PATH"' >> /app/pythia.sh && \
echo 'export PYENV_VIRTUALENV_DISABLE_PROMPT=1' >> /app/pythia.sh && \
echo 'eval "$(pyenv init -)"' >> /app/pythia.sh && \
echo 'eval "$(pyenv virtualenv-init -)"' >> /app/pythia.sh && \
echo "pyenv activate pythia-3.7.9" >> /app/pythia.sh && \
echo "python /app/pythia/pythia.py \$@" >> /app/pythia.sh && \
echo "pyenv deactivate" && \
chmod 755 /app/pythia.sh

ENTRYPOINT ["/app/pythia.sh"]
CMD ["-h"]
