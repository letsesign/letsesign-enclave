# canoni

`canoni` is a command line tool for converting a local docker image into a *canonicalized* docker image so that image reproducibility can be achieved. The canonicalization process simply removes any randomness during a docker build. `canoni` is based on [go-containerregistry](https://github.com/google/go-containerregistry).

## How to build

1. Install a specific version of `go` for reproducibility:
   
   ```
   sudo rm -rf /usr/local/go
   wget -qO- https://go.dev/dl/go1.17.7.linux-amd64.tar.gz | tar xz
   sudo mv go /usr/local/go
   echo 'GOPATH=$HOME/go' >> ~/.bashrc; echo 'PATH=$PATH:/usr/local/go/bin:$GOPATH/bin' >> ~/.bashrc 
   ```
   
2. Build and install `canoni`:
   
   ```
   go install canoni.go
   ```

## How to use

   Let `REPOSITORY:TAG` denote the name of the local docker image to be canonicalized: 
   ```
   canoni REPOSITORY:TAG 
   ```
   
   The canonicalized docker image will be generated and stored at the local with the name being `REPOSITORY-canoni:TAG`. It can be checked using the `docker images` command.
