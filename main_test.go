package main

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestGreeting(t *testing.T) {
	if got, want := greeting(), "Hello, World!"; got != want {
		t.Errorf("greeting() = %q, want %q", got, want)
	}
}

func TestVersionDefault(t *testing.T) {
	// Guards the -ldflags contract: the variable must exist and be settable.
	if version == "" {
		t.Error("version must never be empty; it defaults to \"dev\"")
	}
}

func TestRoutes(t *testing.T) {
	// The probe paths are the chart's livenessProbe.path and
	// readinessProbe.path defaults; a rename here breaks a default install.
	cases := []struct {
		path   string
		status int
		body   string
	}{
		{"/", http.StatusOK, "Hello, World!\n"},
		{"/healthz", http.StatusOK, "ok\n"},
		{"/readyz", http.StatusOK, "ok\n"},
		{"/nothing-here", http.StatusNotFound, ""},
	}

	handler := routes()
	for _, tc := range cases {
		t.Run(tc.path, func(t *testing.T) {
			rec := httptest.NewRecorder()
			handler.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, tc.path, nil))

			if rec.Code != tc.status {
				t.Errorf("GET %s = %d, want %d", tc.path, rec.Code, tc.status)
			}
			if tc.body != "" && rec.Body.String() != tc.body {
				t.Errorf("GET %s body = %q, want %q", tc.path, rec.Body.String(), tc.body)
			}
		})
	}
}

func TestServeHTTPStopsWithTheContext(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	errs := make(chan error, 1)
	go func() { errs <- serveHTTP(ctx, "127.0.0.1:0") }()

	cancel()
	select {
	case err := <-errs:
		if err != nil {
			t.Errorf("serveHTTP returned %v, want a clean shutdown", err)
		}
	case <-time.After(10 * time.Second):
		t.Fatal("serveHTTP did not return after its context was canceled")
	}
}

func TestServeHTTPReportsAListenFailure(t *testing.T) {
	if err := serveHTTP(context.Background(), "not-an-address"); err == nil {
		t.Error("serveHTTP must return the listen error, not nil")
	}
}
