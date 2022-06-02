FROM scratch

# Add https://cdn.amazonlinux.com/os-images/2.0.20220419.0/container/
ADD amzn2-container-raw-2.0.20220419.0-x86_64.tar.xz /

WORKDIR /

# install requirements
COPY packages.yumtx packages.yumtx
RUN yum load-transaction -y packages.yumtx

# install rust
COPY rustup-init.sh rustup-init.sh
RUN chmod +x rustup-init.sh
RUN ./rustup-init.sh -y --default-toolchain 1.50.0 --profile minimal

# build aws-nitro-enclaves-nsm-api
COPY src/v0.2.1.tar.gz v0.2.1.tar.gz
RUN tar zxvf v0.2.1.tar.gz
RUN mv aws-nitro-enclaves-nsm-api-0.2.1 aws-nitro-enclaves-nsm-api
COPY Cargo.lock aws-nitro-enclaves-nsm-api/Cargo.lock
RUN source $HOME/.cargo/env && cargo build --manifest-path=aws-nitro-enclaves-nsm-api/Cargo.toml --release -p nsm-lib
CMD ["/bin/bash"]
