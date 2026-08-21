package main

import "testing"

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
