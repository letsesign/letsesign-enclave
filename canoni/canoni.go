package main

import (
	"os"
    "os/exec"
    "fmt"
    "strings"
    "time"
	v1 "github.com/google/go-containerregistry/pkg/v1"
	"github.com/google/go-containerregistry/pkg/name"
	"github.com/google/go-containerregistry/pkg/v1/tarball"
	"github.com/google/go-containerregistry/pkg/v1/mutate"
)

func Canonicalize(img v1.Image) (v1.Image, error) {
	// Set all timestamps to 0
	created := time.Time{}
	img, err := mutate.Time(img, created)
	if err != nil {
		return nil, err
	}

	cf, err := img.ConfigFile()
	if err != nil {
		return nil, err
	}

	// Get rid of host-dependent random config
	cfg := cf.DeepCopy()
	cfg.Container = ""
	cfg.Config.Hostname = ""
	cfg.Config.Image = ""
	cfg.DockerVersion = ""

	return mutate.ConfigFile(img, cfg)
}

func main() {
    // Check the input argument
    if(len(os.Args[1:]) != 1) {
        fmt.Println("Usage: canoni REPOSITORY:TAG")
        os.Exit(1)
    }
    oldName := os.Args[1]
    newName := ""
    tmpName := strings.Split(os.Args[1], ":")
    if (len(tmpName) == 2) {
        newName = tmpName[0] + "-canoni:" + tmpName[1]
    } else {
        fmt.Println("Usage: canoni REPOSITORY:TAG")
        os.Exit(1)
    }

    // Save the specified docker image
    err := os.MkdirAll(".tmp", os.ModePerm)
    if err != nil {
		panic(err)
    }
    cmd := exec.Command("docker", "save", oldName, "-o", ".tmp/" + oldName + ".tar")
    out, err := cmd.CombinedOutput()
    if err != nil {
        fmt.Println(string(out))
		panic(err)
    }


    // Canonicalize the saved docker image
	tag, err := name.NewTag(oldName)
	if err != nil {
		panic(err)
	}
	img, err := tarball.ImageFromPath(".tmp/" + oldName + ".tar", &tag)
	if err != nil {
		panic(err)
	}
    img, err = Canonicalize(img)
	newTag, err := name.NewTag(newName)
	if err != nil {
		panic(err)
	}
	f, err := os.Create(".tmp/" + newName + ".tar")
	if err != nil {
		panic(err)
	}
	defer f.Close()
	if err := tarball.Write(newTag, img, f); err != nil {
		panic(err)
	}

    // Import the canonicalized docker image
    cmd = exec.Command("docker", "load", "-i", ".tmp/" + newName + ".tar")
    out, err = cmd.CombinedOutput()
    if err != nil {
        fmt.Println(string(out))
		panic(err)
    }

    // Clean up
    cmd = exec.Command("docker", "image", "prune", "-f")
    out, err = cmd.CombinedOutput()
    if err != nil {
        fmt.Println(string(out))
		panic(err)
    }
    cmd = exec.Command("rm", "-rf", ".tmp/")
    out, err = cmd.CombinedOutput()
    if err != nil {
        fmt.Println(string(out))
		panic(err)
    }
}
