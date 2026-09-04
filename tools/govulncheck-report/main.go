// Command govulncheck-report turns a `govulncheck -format json` stream into a
// markdown report and a machine-readable summary.
//
// It is a CI helper, but it is deliberately usable on its own:
//
//	govulncheck -format json ./... > govulncheck.json
//	go run ./tools/govulncheck-report -json govulncheck.json
//
// Finding vulnerabilities is not an error; only a scanner that failed to
// produce a usable report is, which is what -fail-on-scanner-error gates on.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"strconv"
	"strings"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "govulncheck-report: %v\n", err)
		os.Exit(1)
	}
}

func run() error {
	var (
		reportPath  = flag.String("json", "govulncheck.json", "path to the `govulncheck -format json` output")
		stderrPath  = flag.String("stderr", "", "path to the stderr captured from govulncheck")
		exitPath    = flag.String("exit-file", "", "path to a file holding the govulncheck exit code")
		mode        = flag.String("mode", modeFull, "report mode: full (every finding) or fixable (only findings with a published fix)")
		outPath     = flag.String("out", "", "write the markdown report here (default: stdout)")
		summaryPath = flag.String("summary", "", "write the JSON summary here")
		maxRows     = flag.Int("max-rows", 50, "maximum number of table rows to render")
		stepSummary = flag.Bool("step-summary", true, "append the report to $GITHUB_STEP_SUMMARY when that variable is set")
		ghOutput    = flag.Bool("github-output", true, "append counts to $GITHUB_OUTPUT when that variable is set")
		failOnError = flag.Bool("fail-on-scanner-error", false, "exit non-zero when govulncheck itself failed")
	)
	flag.Parse()

	if *mode != modeFull && *mode != modeFixable {
		return fmt.Errorf("invalid -mode %q, want %q or %q", *mode, modeFull, modeFixable)
	}

	exitCode, err := readExitCode(*exitPath)
	if err != nil {
		return err
	}

	report, err := os.Open(*reportPath)
	if err != nil {
		return fmt.Errorf("open govulncheck report: %w", err)
	}
	defer report.Close()

	summary := analyze(report, exitCode)
	markdown := renderMarkdown(summary, *mode, readOptional(*stderrPath), *maxRows)

	if *outPath == "" {
		if _, err := fmt.Print(markdown); err != nil {
			return fmt.Errorf("write markdown report: %w", err)
		}
	} else if err := os.WriteFile(*outPath, []byte(markdown), 0o644); err != nil {
		return fmt.Errorf("write markdown report: %w", err)
	}

	if *summaryPath != "" {
		encoded, err := json.MarshalIndent(summary, "", "  ")
		if err != nil {
			return fmt.Errorf("encode summary: %w", err)
		}
		if err := os.WriteFile(*summaryPath, append(encoded, '\n'), 0o644); err != nil {
			return fmt.Errorf("write summary: %w", err)
		}
	}

	if *stepSummary {
		if err := appendFile(os.Getenv("GITHUB_STEP_SUMMARY"), markdown); err != nil {
			return err
		}
	}
	if *ghOutput {
		if err := appendFile(os.Getenv("GITHUB_OUTPUT"), githubOutputs(summary)); err != nil {
			return err
		}
	}

	if summary.ScannerError && *failOnError {
		return fmt.Errorf("govulncheck failed before producing a usable report (exit code %d)", summary.ExitCode)
	}
	return nil
}

func githubOutputs(summary Summary) string {
	return fmt.Sprintf("scanner-error=%t\nfinding-count=%d\nfixable-count=%d\ncalled-count=%d\n",
		summary.ScannerError, summary.FindingCount, summary.FixableFindingCount, summary.CalledFindingCount)
}

// readExitCode reads the exit code govulncheck was recorded with. An empty path
// means "not captured", which is treated as a clean exit; a path that was given
// but cannot be read is an error, so a broken capture never looks like success.
func readExitCode(path string) (int, error) {
	if path == "" {
		return 0, nil
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return 0, fmt.Errorf("read exit code: %w", err)
	}
	value := strings.TrimSpace(string(raw))
	code, err := strconv.Atoi(value)
	if err != nil {
		return 0, fmt.Errorf("parse exit code %q: %w", value, err)
	}
	return code, nil
}

func readOptional(path string) string {
	if path == "" {
		return ""
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return ""
	}
	return string(raw)
}

func appendFile(path, content string) error {
	if path == "" {
		return nil
	}
	file, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return fmt.Errorf("open %s: %w", path, err)
	}
	defer file.Close()
	if _, err := file.WriteString(content); err != nil {
		return fmt.Errorf("write %s: %w", path, err)
	}
	return file.Close()
}
