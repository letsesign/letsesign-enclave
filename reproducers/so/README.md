# so-Reproducer

## How to use
```
cp ../../enclave/base/amzn2-container-raw-2.0.20220419.0-x86_64.tar.xz .
docker build -t so-reproducer .
docker create --name extractor so-reproducer
docker cp extractor:/aws-nitro-enclaves-nsm-api/target/release/libnsm.so .
docker rm extractor
diff ./libnsm.so ../../enclave/packages/so/libnsm.so
```
