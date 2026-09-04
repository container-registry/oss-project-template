package main

import (
	"encoding/json"
	"errors"
	"io"
	"sort"
	"strings"
)

// Reachability levels, ordered from least to most actionable. govulncheck
// emits one finding per level for the same vulnerability, so the levels are
// merged per (vulnerability, module) pair and only the deepest one is kept.
type reachability int

const (
	reachRequired reachability = iota // the module is in the build, nothing more
	reachImported                     // a vulnerable package is imported
	reachCalled                       // a vulnerable symbol is reachable from this code
)

func (r reachability) String() string {
	switch r {
	case reachCalled:
		return "Called"
	case reachImported:
		return "Imported"
	default:
		return "Required"
	}
}

// Finding is one deduplicated (vulnerability, module) pair.
type Finding struct {
	ID           string `json:"id"`
	Module       string `json:"module"`
	Version      string `json:"version"`
	FixedVersion string `json:"fixedVersion"`
	Reachability string `json:"reachability"`
	Trace        string `json:"trace,omitempty"`
	Summary      string `json:"summary"`

	level reachability
}

// Summary is the machine-readable side of a render, written next to the
// markdown so later workflow steps can branch on it without re-parsing.
type Summary struct {
	ScannerError        bool      `json:"scannerError"`
	ExitCode            int       `json:"exitCode"`
	FindingCount        int       `json:"findingCount"`
	FixableFindingCount int       `json:"fixableFindingCount"`
	CalledFindingCount  int       `json:"calledFindingCount"`
	ParseErrors         []string  `json:"parseErrors"`
	ScannerVersion      string    `json:"scannerVersion,omitempty"`
	GoVersion           string    `json:"goVersion,omitempty"`
	Findings            []Finding `json:"findings"`
}

// govulncheck -format json emits a stream of concatenated JSON objects, each
// carrying exactly one of these keys. Unknown keys (SBOM, progress) decode
// into the zero value and are ignored.
type message struct {
	Config  *configMessage `json:"config"`
	OSV     *osvEntry      `json:"osv"`
	Finding *rawFinding    `json:"finding"`
}

type configMessage struct {
	ScannerName    string `json:"scanner_name"`
	ScannerVersion string `json:"scanner_version"`
	GoVersion      string `json:"go_version"`
}

type osvEntry struct {
	ID       string `json:"id"`
	Summary  string `json:"summary"`
	Details  string `json:"details"`
	Affected []struct {
		Package struct {
			Name string `json:"name"`
		} `json:"package"`
	} `json:"affected"`
}

type rawFinding struct {
	OSV          string  `json:"osv"`
	FixedVersion string  `json:"fixed_version"`
	Trace        []frame `json:"trace"`
}

type frame struct {
	Module   string `json:"module"`
	Version  string `json:"version"`
	Package  string `json:"package"`
	Function string `json:"function"`
	Receiver string `json:"receiver"`
}

// analyze turns a govulncheck JSON stream plus the process exit code into a
// Summary. It never returns an error: an unreadable report is a scanner error,
// which is reported through the Summary so the caller can still render it.
func analyze(report io.Reader, exitCode int) Summary {
	var (
		parseErrors []string
		sawConfig   bool
		cfg         configMessage
		osvByID     = map[string]osvEntry{}
		findings    []rawFinding
	)

	dec := json.NewDecoder(report)
	for {
		var msg message
		if err := dec.Decode(&msg); err != nil {
			if errors.Is(err, io.EOF) {
				break
			}
			parseErrors = append(parseErrors, err.Error())
			break
		}
		switch {
		case msg.Config != nil:
			sawConfig = true
			cfg = *msg.Config
		case msg.OSV != nil && msg.OSV.ID != "":
			osvByID[msg.OSV.ID] = *msg.OSV
		case msg.Finding != nil && msg.Finding.OSV != "":
			findings = append(findings, *msg.Finding)
		}
	}

	merged := map[string]*Finding{}
	for _, raw := range findings {
		osv := osvByID[raw.OSV]
		module, version, level, trace := describe(raw, osv)
		key := raw.OSV + "\x00" + module
		existing, ok := merged[key]
		if !ok {
			merged[key] = &Finding{
				ID:           raw.OSV,
				Module:       module,
				Version:      version,
				FixedVersion: raw.FixedVersion,
				Reachability: level.String(),
				Trace:        trace,
				Summary:      summarize(osv),
				level:        level,
			}
			continue
		}
		if level > existing.level {
			existing.level = level
			existing.Reachability = level.String()
			existing.Trace = trace
		}
		if existing.FixedVersion == "" {
			existing.FixedVersion = raw.FixedVersion
		}
		if existing.Version == "" {
			existing.Version = version
		}
	}

	out := make([]Finding, 0, len(merged))
	for _, f := range merged {
		out = append(out, *f)
	}
	// Most actionable first: reachable code, then vulnerability ID.
	sort.Slice(out, func(i, j int) bool {
		if out[i].level != out[j].level {
			return out[i].level > out[j].level
		}
		if out[i].ID != out[j].ID {
			return out[i].ID < out[j].ID
		}
		return out[i].Module < out[j].Module
	})

	summary := Summary{
		ExitCode:       exitCode,
		ParseErrors:    parseErrors,
		ScannerVersion: cfg.ScannerVersion,
		GoVersion:      cfg.GoVersion,
		Findings:       out,
	}
	if summary.ParseErrors == nil {
		summary.ParseErrors = []string{}
	}
	summary.FindingCount = len(out)
	for _, f := range out {
		if f.FixedVersion != "" {
			summary.FixableFindingCount++
		}
		if f.Reachability == reachCalled.String() {
			summary.CalledFindingCount++
		}
	}

	// A scan that produced no config message produced no usable report at all
	// (empty or truncated output). With -format json govulncheck reports
	// vulnerabilities through the stream and still exits 0, so a non-zero exit
	// means the scanner itself failed; exit 3 is reserved for "vulnerabilities
	// found" and is only trusted when findings actually came through.
	summary.ScannerError = len(parseErrors) > 0 ||
		!sawConfig ||
		(exitCode != 0 && exitCode != 3) ||
		(exitCode == 3 && len(out) == 0)

	return summary
}

// describe picks the module the vulnerability lives in. trace[0] is the
// vulnerable frame itself (govulncheck sorts traces from the vulnerable symbol
// outwards to the entry point), so it carries the affected module and the
// version actually in the build.
func describe(raw rawFinding, osv osvEntry) (module, version string, level reachability, trace string) {
	if len(raw.Trace) == 0 {
		return fallbackModule(osv), "", reachRequired, ""
	}
	vuln := raw.Trace[0]
	module, version = vuln.Module, vuln.Version
	if module == "" {
		module = fallbackModule(osv)
	}
	switch {
	case vuln.Function != "":
		level = reachCalled
		trace = symbolLabel(vuln)
	case vuln.Package != "":
		level = reachImported
	default:
		level = reachRequired
	}
	return module, version, level, trace
}

func symbolLabel(f frame) string {
	name := f.Function
	if f.Receiver != "" {
		name = f.Receiver + "." + name
	}
	if pkg := lastPathSegment(f.Package); pkg != "" {
		return pkg + "." + name
	}
	return name
}

func lastPathSegment(path string) string {
	if idx := strings.LastIndex(path, "/"); idx >= 0 {
		return path[idx+1:]
	}
	return path
}

func fallbackModule(osv osvEntry) string {
	for _, affected := range osv.Affected {
		if affected.Package.Name != "" {
			return affected.Package.Name
		}
	}
	return "unknown"
}

func summarize(osv osvEntry) string {
	text := osv.Summary
	if text == "" {
		text = osv.Details
	}
	return shorten(text, 200)
}

func shorten(value string, limit int) string {
	text := strings.Join(strings.Fields(value), " ")
	if len([]rune(text)) <= limit {
		return text
	}
	return string([]rune(text)[:limit-3]) + "..."
}
