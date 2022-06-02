# whl-Reproducer

## How to use
```
cp ../../enclave/base/amzn2-container-raw-2.0.20220419.0-x86_64.tar.xz .
cp ../../enclave/server/requirements-lock.txt .
docker build -t whl-reproducer .
docker create --name extractor whl-reproducer; docker cp extractor:/whl .; docker rm extractor
diff ./whl ../../enclave/packages/whl
```
