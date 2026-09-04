package main

import (
	"fmt"
	"strings"
)

// marker identifies the sticky pull request comment so re-runs update the
// existing comment instead of stacking new ones.
const marker = "<!-- govulncheck-report -->"

const (
	modeFull    = "full"
	modeFixable = "fixable"
)

// renderMarkdown builds the report body. In fixable mode only findings with a
// known fixed version are listed, because those are the ones a reviewer can act
// on inside the pull request.
func renderMarkdown(summary Summary, mode string, scannerStderr string, maxRows int) string {
	shown := summary.Findings
	if mode == modeFixable {
		shown = fixableOnly(summary.Findings)
	}

	var b strings.Builder
	b.WriteString(marker + "\n")
	b.WriteString("## govulncheck\n\n")

	switch {
	case summary.ScannerError:
		fmt.Fprintf(&b, "**govulncheck did not produce a usable report** (exit code %d).\n\n", summary.ExitCode)
		details := strings.Join(summary.ParseErrors, "; ")
		if details == "" {
			details = scannerStderr
		}
		if details = shorten(details, 500); details == "" {
			details = "no diagnostics captured on stderr"
		}
		fmt.Fprintf(&b, "```\n%s\n```\n", details)
		if len(shown) > 0 {
			fmt.Fprintf(&b, "\nFindings parsed before the failure (%d of %d):\n\n", len(shown), summary.FindingCount)
			writeTable(&b, shown, maxRows)
		}
	case len(shown) == 0 && mode == modeFixable && summary.FindingCount > 0:
		fmt.Fprintf(&b, "No fixable vulnerabilities. govulncheck reported %s without a fixed version.\n",
			plural(summary.FindingCount, "vulnerability", "vulnerabilities"))
	case len(shown) == 0:
		b.WriteString("No known vulnerabilities in the module dependency graph.\n")
	default:
		writeHeadline(&b, summary, shown, mode)
		b.WriteString("\n")
		writeTable(&b, shown, maxRows)
		writeFootnotes(&b, shown)
	}

	fmt.Fprintf(&b, "\n<sub>govulncheck %s on %s, exit code %d. The full JSON report is attached to the workflow run as the `vulnerability-check` artifact.</sub>\n",
		fallback(summary.ScannerVersion, "unknown"), fallback(summary.GoVersion, "unknown"), summary.ExitCode)

	return b.String()
}

func writeHeadline(b *strings.Builder, summary Summary, shown []Finding, mode string) {
	if mode == modeFixable {
		fmt.Fprintf(b, "**%s with a published fix** out of %d total.",
			plural(len(shown), "vulnerability", "vulnerabilities"), summary.FindingCount)
	} else {
		fmt.Fprintf(b, "**%s** in the module dependency graph, %d with a published fix.",
			plural(len(shown), "vulnerability", "vulnerabilities"), summary.FixableFindingCount)
	}
	if called := countCalled(shown); called > 0 {
		fmt.Fprintf(b, " %d reachable from this module's code.", called)
	}
	b.WriteString("\n")
}

func writeTable(b *strings.Builder, findings []Finding, maxRows int) {
	b.WriteString("| Vulnerability | Module | In use | Fixed in | Reachability | Summary |\n")
	b.WriteString("| :--- | :--- | :--- | :--- | :--- | :--- |\n")

	rows := findings
	if maxRows > 0 && len(rows) > maxRows {
		rows = rows[:maxRows]
	}
	for _, f := range rows {
		reach := f.Reachability
		if f.Trace != "" {
			reach = fmt.Sprintf("%s (%s)", reach, code(f.Trace))
		}
		fmt.Fprintf(b, "| [%s](https://pkg.go.dev/vuln/%s) | %s | %s | %s | %s | %s |\n",
			escape(f.ID), f.ID, code(f.Module), code(f.Version), code(f.FixedVersion), reach, escape(f.Summary))
	}
	if len(rows) < len(findings) {
		fmt.Fprintf(b, "\n_Showing %d of %d findings; see the workflow artifact for the rest._\n", len(rows), len(findings))
	}
}

func writeFootnotes(b *strings.Builder, findings []Finding) {
	for _, f := range findings {
		if f.Module == "stdlib" {
			b.WriteString("\n_`stdlib` findings are fixed by raising the `go` directive in `go.mod`._\n")
			return
		}
	}
}

func fixableOnly(findings []Finding) []Finding {
	out := make([]Finding, 0, len(findings))
	for _, f := range findings {
		if f.FixedVersion != "" {
			out = append(out, f)
		}
	}
	return out
}

func countCalled(findings []Finding) int {
	count := 0
	for _, f := range findings {
		if f.Reachability == reachCalled.String() {
			count++
		}
	}
	return count
}

func plural(count int, singular, pluralForm string) string {
	if count == 1 {
		return fmt.Sprintf("%d %s", count, singular)
	}
	return fmt.Sprintf("%d %s", count, pluralForm)
}

func escape(value string) string {
	value = strings.ReplaceAll(value, "|", `\|`)
	value = strings.ReplaceAll(value, "\n", " ")
	if value == "" {
		return "-"
	}
	return value
}

func code(value string) string {
	if value == "" {
		return "-"
	}
	return "`" + strings.ReplaceAll(value, "`", "") + "`"
}

func fallback(value, def string) string {
	if value == "" {
		return def
	}
	return value
}
