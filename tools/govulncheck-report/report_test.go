package main

import (
	"os"
	"strings"
	"testing"
)

// The testdata fixtures are reduced from real `govulncheck -format json` runs:
// findings.json comes from a module pinned to golang.org/x/text v0.3.0 built
// with Go 1.26.4, clean.json from this repository. OSV fields the renderer does
// not read were stripped to keep the fixtures reviewable.

func analyzeFixture(t *testing.T, name string, exitCode int) Summary {
	t.Helper()
	file, err := os.Open("testdata/" + name)
	if err != nil {
		t.Fatalf("open fixture: %v", err)
	}
	defer file.Close()
	return analyze(file, exitCode)
}

func TestAnalyzeFindings(t *testing.T) {
	summary := analyzeFixture(t, "findings.json", 0)

	if summary.ScannerError {
		t.Fatalf("findings must not be reported as a scanner error: %+v", summary.ParseErrors)
	}
	// The fixture holds 18 raw findings; govulncheck emits one per detail level,
	// so module/package/symbol findings collapse into 14 (vulnerability, module) pairs.
	if summary.FindingCount != 14 {
		t.Errorf("FindingCount = %d, want 14", summary.FindingCount)
	}
	if summary.FixableFindingCount != 14 {
		t.Errorf("FixableFindingCount = %d, want 14", summary.FixableFindingCount)
	}
	if summary.CalledFindingCount != 1 {
		t.Errorf("CalledFindingCount = %d, want 1", summary.CalledFindingCount)
	}
	if summary.ScannerVersion != "v1.4.0" || summary.GoVersion != "go1.26.4" {
		t.Errorf("scanner metadata = %q/%q", summary.ScannerVersion, summary.GoVersion)
	}

	first := summary.Findings[0]
	if first.ID != "GO-2021-0113" {
		t.Errorf("reachable finding must sort first, got %q", first.ID)
	}
	if first.Reachability != "Called" || first.Trace != "language.Parse" {
		t.Errorf("first finding = %q/%q, want Called/language.Parse", first.Reachability, first.Trace)
	}
	if first.Module != "golang.org/x/text" || first.Version != "v0.3.0" || first.FixedVersion != "v0.3.7" {
		t.Errorf("first finding versions = %q %q -> %q", first.Module, first.Version, first.FixedVersion)
	}
}

func TestAnalyzeCleanReport(t *testing.T) {
	summary := analyzeFixture(t, "clean.json", 0)

	if summary.ScannerError {
		t.Error("clean report must not be a scanner error")
	}
	if summary.FindingCount != 0 {
		t.Errorf("FindingCount = %d, want 0", summary.FindingCount)
	}
	// govulncheck streams every candidate OSV entry even when nothing matches,
	// so an empty finding list is the only signal of a clean scan.
	if len(summary.Findings) != 0 {
		t.Errorf("Findings = %+v, want none", summary.Findings)
	}
}

func TestAnalyzeScannerErrors(t *testing.T) {
	tests := []struct {
		name     string
		fixture  string
		exitCode int
	}{
		{"empty output", "empty.json", 0},
		{"truncated output", "truncated.json", 0},
		{"clean report but non-zero exit", "clean.json", 1},
		{"exit code 3 without findings", "clean.json", 3},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if summary := analyzeFixture(t, tc.fixture, tc.exitCode); !summary.ScannerError {
				t.Errorf("ScannerError = false, want true (exit %d)", tc.exitCode)
			}
		})
	}
}

func TestAnalyzeVulnerabilitiesFoundExitCode(t *testing.T) {
	// Older govulncheck releases exit 3 once vulnerabilities are found; that is
	// a result, not a scanner failure.
	if summary := analyzeFixture(t, "findings.json", 3); summary.ScannerError {
		t.Error("exit code 3 with findings must not be a scanner error")
	}
}

func TestRenderFixableModeDropsUnfixedFindings(t *testing.T) {
	summary := Summary{
		FindingCount:        2,
		FixableFindingCount: 1,
		Findings: []Finding{
			{ID: "GO-1", Module: "example.com/a", Version: "v1.0.0", FixedVersion: "v1.0.1", Reachability: "Called", Trace: "a.Do", Summary: "fixed"},
			{ID: "GO-2", Module: "example.com/b", Version: "v2.0.0", Reachability: "Required", Summary: "no fix yet"},
		},
	}

	fixable := renderMarkdown(summary, modeFixable, "", 50)
	if !strings.Contains(fixable, "GO-1") || strings.Contains(fixable, "GO-2") {
		t.Errorf("fixable mode must list only fixed findings:\n%s", fixable)
	}
	if !strings.Contains(fixable, "**1 vulnerability with a published fix** out of 2 total.") {
		t.Errorf("unexpected headline:\n%s", fixable)
	}
	if !strings.HasPrefix(fixable, marker) {
		t.Error("report must start with the sticky comment marker")
	}

	full := renderMarkdown(summary, modeFull, "", 50)
	if !strings.Contains(full, "GO-2") {
		t.Errorf("full mode must list every finding:\n%s", full)
	}
}

func TestRenderFixableModeWithoutFixes(t *testing.T) {
	summary := Summary{
		FindingCount: 1,
		Findings:     []Finding{{ID: "GO-2", Module: "example.com/b", Reachability: "Required"}},
	}
	body := renderMarkdown(summary, modeFixable, "", 50)
	if !strings.Contains(body, "No fixable vulnerabilities") {
		t.Errorf("unexpected body:\n%s", body)
	}
}

func TestRenderScannerError(t *testing.T) {
	summary := Summary{ScannerError: true, ExitCode: 2}
	body := renderMarkdown(summary, modeFull, "go: downloading failed\n", 50)

	if !strings.Contains(body, "did not produce a usable report") {
		t.Errorf("missing failure headline:\n%s", body)
	}
	if !strings.Contains(body, "go: downloading failed") {
		t.Errorf("stderr must be surfaced:\n%s", body)
	}
}

func TestRenderEscapesTableCells(t *testing.T) {
	summary := Summary{
		FindingCount: 1,
		Findings:     []Finding{{ID: "GO-1", Module: "example.com/a", Summary: "breaks | tables", Reachability: "Required"}},
	}
	body := renderMarkdown(summary, modeFull, "", 50)
	if !strings.Contains(body, `breaks \| tables`) {
		t.Errorf("pipe not escaped:\n%s", body)
	}
}

func TestRenderTruncatesLongTables(t *testing.T) {
	summary := Summary{FindingCount: 3}
	for i := range 3 {
		summary.Findings = append(summary.Findings, Finding{ID: string(rune('A' + i)), Module: "m", Reachability: "Required"})
	}
	body := renderMarkdown(summary, modeFull, "", 2)
	if !strings.Contains(body, "_Showing 2 of 3 findings") {
		t.Errorf("missing truncation notice:\n%s", body)
	}
}

func TestGitHubOutputs(t *testing.T) {
	got := githubOutputs(Summary{ScannerError: true, FindingCount: 4, FixableFindingCount: 3, CalledFindingCount: 1})
	want := "scanner-error=true\nfinding-count=4\nfixable-count=3\ncalled-count=1\n"
	if got != want {
		t.Errorf("githubOutputs() = %q, want %q", got, want)
	}
}

func TestReadExitCode(t *testing.T) {
	if code, err := readExitCode(""); err != nil || code != 0 {
		t.Errorf("readExitCode(\"\") = %d, %v", code, err)
	}
	path := t.TempDir() + "/exit"
	if err := os.WriteFile(path, []byte("3\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if code, err := readExitCode(path); err != nil || code != 3 {
		t.Errorf("readExitCode(file) = %d, %v", code, err)
	}
	// A capture that was requested but is unreadable must not look like success.
	if _, err := readExitCode(path + ".missing"); err == nil {
		t.Error("missing exit-code file must be an error")
	}
}
