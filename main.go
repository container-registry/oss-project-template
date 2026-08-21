// Command app is the minimal program the template's build, test and release
// pipeline runs against. Replace it with the real project; keep the version
// variable, which `task release-assets` and the Dockerfile stamp at build time.
package main

import (
	"flag"
	"fmt"
	"os"
)

// version is set at build time with -ldflags "-X main.version=...".
var version = "dev"

func main() {
	showVersion := flag.Bool("version", false, "print the version and exit")
	flag.Parse()

	out := greeting()
	if *showVersion {
		out = version
	}

	if _, err := fmt.Fprintln(os.Stdout, out); err != nil {
		fmt.Fprintln(os.Stderr, "write failed:", err)
		os.Exit(1)
	}
}

func greeting() string {
	return "Hello, World!"
}
