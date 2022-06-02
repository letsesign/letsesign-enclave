FROM scratch

# Add https://cdn.amazonlinux.com/os-images/2.0.20220419.0/container/
ADD amzn2-container-raw-2.0.20220419.0-x86_64.tar.xz /

WORKDIR /

# install requirements
COPY packages.yumtx packages.yumtx
RUN yum load-transaction -y packages.yumtx

# downlaod rpm
COPY enclave-rpm-packages.txt enclave-rpm-packages.txt
COPY download.sh download.sh
RUN ./download.sh
CMD ["/bin/bash"]
