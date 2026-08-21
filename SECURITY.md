# Security Policy

## Reporting a Vulnerability

**Do not open a public issue, discussion, or pull request for a security problem.**

Report it privately, either way:

- **GitHub** (preferred): [open a private security advisory](https://github.com/{{ORG_NAME}}/{{REPO_NAME}}/security/advisories/new).
  This keeps the report, the discussion, the fix, and the eventual CVE in one place.
- **Email**: {{SECURITY_EMAIL}}. Say so in the first message if you need an encrypted channel.

Please include whatever you have:

- affected version, commit, or image digest
- component and configuration involved
- reproduction steps or a proof of concept
- the impact you believe it has
- whether the issue is already public or known to anyone else

Reports in any language are fine, and a partial report is better than no report.

## What Happens Next

| Stage | Target |
|-------|--------|
| Acknowledgement that a human has the report | 3 working days |
| Initial assessment: valid, severity, affected versions | 10 working days |
| Fix or documented mitigation for supported versions | driven by severity, tracked in the advisory |
| Public advisory and release | coordinated with the reporter |

We use CVSS v3.1 to communicate severity. You will get progress updates as the assessment moves, without having
to ask. If a report is rejected you get the reasoning, not silence.

## Coordinated Disclosure

We follow coordinated vulnerability disclosure.

- Default embargo is **90 days** from acknowledgement, or until a fix ships, whichever comes first.
- We will agree any change to that window with you rather than announce one.
- We request a CVE and publish a GitHub Security Advisory when the fix is released.
- Reporters are credited by name or handle in the advisory unless they ask not to be.
- If a vulnerability is being actively exploited, we may shorten the embargo and will tell you when we do.

We will not pursue or support legal action against anyone who researches and reports in good faith under this
policy, keeps to the embargo, and does not access, modify, or exfiltrate other people's data.

There is no bug bounty for this project.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest minor release | Yes |
| Previous minor release | Security fixes only |
| Older | No |

Fixes land on the latest release first. Backports to the previous minor are made for high and critical issues.

## Scope

In scope: the source, the build and release pipeline, published release artifacts, and container images
produced by this repository.

Out of scope: vulnerabilities in dependencies with no exploitable path through this project (report those
upstream), findings that require an already-compromised host, and issues that only affect an unsupported
version.

<!-- Replace this paragraph with anything specific to the project: components that intentionally accept
     untrusted input, deployment assumptions the threat model depends on, or known accepted risks. -->

## What We Publish With Each Release

- A signed release and container image, verifiable with [cosign](https://github.com/sigstore/cosign).
- A Software Bill of Materials in SPDX JSON, attached to the release and attested to the image.
- Build provenance attestation.

`docs/RELEASES.md` has the verification commands.

## Upstream Reports

This project is maintained as open source. Where it packages or forks another project, vulnerabilities in that
upstream are reported to its maintainers under their policy, and we track the fix here.
