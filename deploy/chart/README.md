# oss-project-template

A Helm chart for the service this repository ships.

## Install

The chart is published as an OCI artifact. Where it is published is a property
of the repository that ships it, not of the chart, so substitute the repository
path for `CHART_REPOSITORY` below. Every chart release prints the exact command
in its release notes.

<!-- x-release-please-start-version -->
```sh
helm install oss-project-template \
  oci://CHART_REPOSITORY/oss-project-template \
  --version 0.0.0
```
<!-- x-release-please-end -->

The image tag defaults to the chart's `appVersion`. Set `image.tag` to pin a
different application release.

## Verifying the chart signature

Every released chart is signed keyless with Sigstore from the release workflow,
so there is no key to distribute: the signing identity is the workflow itself.
Substitute the repository path for `CHART_REPOSITORY` and the owning repository
for `OWNER/REPO`; the release notes carry both, filled in, next to the digest
that was signed.

<!-- x-release-please-start-version -->
```sh
cosign verify CHART_REPOSITORY/oss-project-template:0.0.0 \
  --certificate-identity-regexp '^https://github\.com/OWNER/REPO/\.github/workflows/publish-chart\.yml@' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```
<!-- x-release-please-end -->

Verify by digest rather than by tag when it matters: a tag can be repointed at
a different artifact after the signature was made.

## What the chart does

- Renders a Deployment, a Service and, by default, a ServiceAccount.
- Nothing is generated at render time, so Argo CD and Flux see no drift. CI
  renders the GitOps scenario twice and fails on any difference.
- A closed `values.schema.json` rejects unknown or mistyped values before
  anything reaches the cluster. The exceptions are the values passed straight
  through to Kubernetes, `podSecurityContext`, `securityContext`, `affinity`
  and `tolerations`: they are typed as objects only, so that a Kubernetes
  field the schema predates still works.
- The defaults satisfy the restricted Pod Security Standard.

Adding a value means touching three places: `values.yaml` (with a `# --`
helm-docs comment), `values.schema.json`, and a test under `tests/`. Then run
`task helm:docs` to regenerate this file.

## Maintainers

| Name | Email | Url |
| ---- | ------ | --- |
| Container Registry Maintainers | <oss@container-registry.com> |  |

## Requirements

Kubernetes: `>=1.28.0-0`

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| affinity | object | `{}` | Affinity rules for pod placement. |
| args | list | `["-serve"]` | Container arguments. The template's demo image only stays up with `-serve`; empty this when `image.repository` points at your own service. |
| commonLabels | object | `{}` | Labels added to every resource. |
| extraEnv | list | `[]` | Extra environment variables for the container, as a list of EnvVar objects. |
| fullnameOverride | string | `""` | Override the fully qualified resource name. |
| image.pullPolicy | string | `"IfNotPresent"` | Image pull policy. |
| image.repository | string | `"ghcr.io/container-registry/oss-project-template"` | Image repository. Rewritten by `task bootstrap`. |
| image.tag | string | `""` | Image tag. Defaults to the chart's appVersion. |
| imagePullSecrets | list | `[]` | Names of image pull Secrets in the release namespace. |
| livenessProbe.enabled | bool | `true` | Enable the HTTP liveness probe. |
| livenessProbe.initialDelaySeconds | int | `5` | Seconds before the first liveness probe. |
| livenessProbe.path | string | `"/healthz"` | Path the liveness probe requests on the container port. |
| livenessProbe.periodSeconds | int | `10` | Seconds between liveness probes. |
| nameOverride | string | `""` | Override the chart name used in resource names. |
| nodeSelector | object | `{}` | Node selector for pod placement. |
| podAnnotations | object | `{}` | Annotations added to the pod. |
| podSecurityContext | object | `{"fsGroup":65532,"runAsGroup":65532,"runAsNonRoot":true,"runAsUser":65532,"seccompProfile":{"type":"RuntimeDefault"}}` | Pod security context. The defaults satisfy the restricted Pod Security Standard. |
| readinessProbe.enabled | bool | `true` | Enable the HTTP readiness probe. |
| readinessProbe.initialDelaySeconds | int | `5` | Seconds before the first readiness probe. |
| readinessProbe.path | string | `"/readyz"` | Path the readiness probe requests on the container port. |
| readinessProbe.periodSeconds | int | `10` | Seconds between readiness probes. |
| replicaCount | int | `1` | Number of replicas. |
| resources | object | `{"limits":{"memory":"128Mi"},"requests":{"cpu":"50m","memory":"64Mi"}}` | Resource requests and limits. Set on purpose: the pack's linters fail on unset resources. |
| securityContext | object | `{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]},"readOnlyRootFilesystem":true,"runAsNonRoot":true}` | Container security context. The defaults satisfy the restricted Pod Security Standard. |
| service.port | int | `8080` | Service port. |
| service.targetPort | int | `8080` | Container port the Service forwards to. |
| service.type | string | `"ClusterIP"` | Service type. |
| serviceAccount.annotations | object | `{}` | Annotations for the ServiceAccount, for example a cloud IAM binding. |
| serviceAccount.automountServiceAccountToken | bool | `false` | Mount the API token into the pod. The service does not talk to the API server. |
| serviceAccount.create | bool | `true` | Create a ServiceAccount for the workload. |
| serviceAccount.name | string | `""` | Name of the ServiceAccount. Defaults to the release fullname when created, `default` otherwise. |
| tolerations | list | `[]` | Tolerations for pod placement. |
