# rpm-Reproducer

## How to use
```
cp ../../enclave/base/amzn2-container-raw-2.0.20220419.0-x86_64.tar.xz .
cp ../../enclave/configs/enclave-rpm-packages.txt .
docker build -t rpm-reproducer .
docker create --name extractor rpm-reproducer; docker cp extractor:/rpm .; docker rm extractor
diff ./rpm ../../enclave/packages/rpm
```
