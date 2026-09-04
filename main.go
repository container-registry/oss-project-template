// Command app is the minimal program the template's build, test and release
// pipeline runs against. Replace it with the real project; keep the version
// variable, which `task release-assets` and the Dockerfile stamp at build time.
package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

// version is set at build time with -ldflags "-X main.version=...".
var version = "dev"

func main() {
	showVersion := flag.Bool("version", false, "print the version and exit")
	// The Helm chart deploys this image with HTTP probes, so the demo must be
	// able to stay up. Serving is opt-in rather than the default because the
	// image smoke test in ci.yml runs the container and waits for it to exit.
	serve := flag.Bool("serve", false, "serve HTTP on -addr until terminated")
	addr := flag.String("addr", ":8080", "address the -serve listener binds")
	flag.Parse()

	if *serve && !*showVersion {
		// SIGTERM is what a Kubernetes eviction sends.
		ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
		defer stop()
		if err := serveHTTP(ctx, *addr); err != nil {
			fmt.Fprintln(os.Stderr, "serve failed:", err)
			os.Exit(1)
		}
		return
	}

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

// routes answers the two paths the chart's probes request, and the greeting on
// the root path. `{$}` matches only "/", so anything else is a 404.
func routes() http.Handler {
	mux := http.NewServeMux()
	health := func(w http.ResponseWriter, _ *http.Request) {
		fmt.Fprintln(w, "ok")
	}
	mux.HandleFunc("GET /healthz", health)
	mux.HandleFunc("GET /readyz", health)
	mux.HandleFunc("GET /{$}", func(w http.ResponseWriter, _ *http.Request) {
		fmt.Fprintln(w, greeting())
	})
	return mux
}

func serveHTTP(ctx context.Context, addr string) error {
	srv := &http.Server{
		Addr:    addr,
		Handler: routes(),
		// Without a header deadline one slow client holds a connection open
		// for as long as it likes.
		ReadHeaderTimeout: 5 * time.Second,
	}

	errs := make(chan error, 1)
	go func() { errs <- srv.ListenAndServe() }()

	select {
	case err := <-errs:
		return err
	case <-ctx.Done():
		// The pod leaves the Service endpoints at the same moment SIGTERM
		// arrives, so in-flight requests are drained rather than reset.
		shutdown, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		return srv.Shutdown(shutdown)
	}
}
