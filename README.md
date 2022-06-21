# Let's eSign Enclave 

```
    .          
    ├── canoni                 # Tool to canonicalize a Docker image for reproducibility
    ├── enclave                # Let's eSign Enclave
    │   ├── base               # Source of Amazon Linux 2 Docker container base image
    │   ├── configs            # Config files for Let's eSign Enclave
    │   ├── packages           # Pre-built packages for Let's eSign Enclave
    │   ├── server             # Server code run within Let's eSign Enclave
    │   └── Dockerfile
    ├── measurements           # Measurements of every Let's eSign Enclave release 
    ├── reproducers            # Containers for reproducing enclave/packages         
    ├── LICENSE
    └── README.md
```

## Introduction

Let's eSign Enclave is the foundation on which [Let's eSign](https://www.letsesign.org), the confidential eSigning service, is built. It is based on [AWS Nitro Enclaves](https://aws.amazon.com/ec2/nitro/nitro-enclaves/), which can be viewed as AWS's own hardware implementation of [trusted execution environment](https://en.wikipedia.org/wiki/Trusted_execution_environment). Let's eSign leverages the feature that [AWS KMS](https://aws.amazon.com/kms/) can be set up so that [only specific AWS Nitro Enclaves instances can access specific AWS KMS keys](https://docs.aws.amazon.com/kms/latest/developerguide/services-nitro-enclaves.html) to achieve confidential eSigning. Check [here](https://github.com/letsesign/letsesign-enclave/tree/main/enclave) for how Let's eSign Enclave works.

The code that a Nitro Enclaves instance runs is decided by its *image*, which can be made from a Docker container image. And every Nitro Enclaves image can be uniquely identified by its [measurements](https://docs.aws.amazon.com/enclaves/latest/user/set-up-attestation.html).

This repository contains the source code for reproducing the Nitro Enclaves image of every Let's eSign Enclave release, while relying parties can tell the identity of the Let's eSign Enclave instance they are interacting with by the corresponding measurements.

## How to reproduce Let's eSign Enclave

### Prepare the build environment

1. Launch an AWS EC2 instance based on Amazon Linux 2 AMI.

2. Install a specific version of `go` for reproducibility:
   
   ```
   sudo rm -rf /usr/local/go
   wget -qO- https://go.dev/dl/go1.17.7.linux-amd64.tar.gz | tar xz
   sudo mv go /usr/local/go
   echo 'GOPATH=$HOME/go' >> ~/.bashrc; echo 'PATH=$PATH:/usr/local/go/bin:$GOPATH/bin' >> ~/.bashrc 
   ```
   
3. Install a specific version of `docker` for reproducibility:
   
   ```
   sudo yum install -y docker-20.10.7-5.amzn2
   sudo systemctl start docker && sudo systemctl enable docker
   ```

4. Install a specific version of `nitro-cli` for reproducibility:
   
   ```
   sudo amazon-linux-extras enable aws-nitro-enclaves-cli > /dev/null 2>&1; sudo yum clean metadata
   sudo yum install -y aws-nitro-enclaves-cli-1.1.0-0.amzn2 aws-nitro-enclaves-cli-devel-1.1.0-0.amzn2
   ```

5. Run the following to execute `docker` and `nitro-cli` as a non-root user:
   
   ```
   sudo gpasswd -a $USER docker
   sudo gpasswd -a $USER ne
   ```
   
6. Log out and back in again for the above to take effect.
   
### Build the Nitro Enclaves image of Let's eSign Enclave

1. Run the following to build the Docker image of Let's eSign Enclave:
   
   ```
   cd enclave/
   docker build -t letsesign-enclave .
   ```
2. Run the following to canonicalize the built Docker image for reproducibility:
   
   ```
   cd canoni/
   go install canoni.go
   canoni letsesign-enclave:latest
   ```
3. Run the following to convert the canonicalized Docker image into a Nitro Enclaves image:
   
   ```
   nitro-cli build-enclave --docker-uri letsesign-enclave-canoni --output-file letsesign-enclave.eif
   ```
   When finished, the image file can be found at the current directory, and the measurements of the Nitro Enclaves image will be showed on the console.
