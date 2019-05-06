FROM res-env

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

COPY . /root/src

RUN /bin/bash -c ". /opt/conda/etc/profile.d/conda.sh && \
    conda activate conda-env-rmexp && \
    cd /root/src && \
    python setup.py install && \
    cd /root/src/app && \
    python setup.py install"

RUN (echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc) \
    && (echo "conda activate conda-env-rmexp" >> ~/.bashrc)

WORKDIR /root/src
