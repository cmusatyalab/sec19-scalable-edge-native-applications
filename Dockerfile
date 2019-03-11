FROM res-env

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

COPY . /root/src

RUN /bin/bash -c ". /opt/conda/etc/profile.d/conda.sh && \
    conda activate resource-management && \
    cd /root/src && \
    python setup.py install && \
    cd /root/src/app && \
    python setup.py install"

RUN /bin/bash /root/src/install.sh

ENTRYPOINT [ "/bin/bash" ]
CMD [ "/bin/bash" ]