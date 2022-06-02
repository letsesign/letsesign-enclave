FROM scratch

# Add https://cdn.amazonlinux.com/os-images/2.0.20220419.0/container/
ADD base/amzn2-container-raw-2.0.20220419.0-x86_64.tar.xz /

WORKDIR /

COPY configs/ configs/

COPY packages/ packages/

COPY server/ server/
RUN chmod +x server/launch.sh

# Remove unnecessary files
RUN rm /etc/shadow
RUN rm /etc/gshadow

CMD ["./server/launch.sh"]
