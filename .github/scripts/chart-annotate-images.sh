#!/usr/bin/env bash
# Append the per-release artifacthub.io/images annotation to a chart's
# Chart.yaml.
#
# It is not committed because the image tag follows the chart's appVersion, and
# it is appended rather than templated because Chart.yaml deliberately keeps
# `annotations:` as its last top-level key.
#
# Usage: chart-annotate-images.sh <chart-dir>
#   IMAGE_REPOSITORY  image without a tag (default: image.repository in values.yaml)
#   APP_VERSION       image tag (default: appVersion in Chart.yaml)
set -euo pipefail

chart_dir="${1:?chart directory is required}"
chart_yaml="${chart_dir}/Chart.yaml"
values_yaml="${chart_dir}/values.yaml"

# The append is only correct while `annotations:` is the final top-level key.
# A key added after it would be swallowed into the annotations map without a
# YAML error if that key happens to be map-valued, so fail loudly here.
last_key=$(grep -E '^[A-Za-z]' "${chart_yaml}" | tail -1 | cut -d: -f1)
if [[ "${last_key}" != "annotations" ]]; then
  echo "Chart.yaml must keep 'annotations' as its last top-level key (found '${last_key}')." >&2
  exit 1
fi

scalar() {
  # First top-level (or, for values.yaml, first) occurrence of `key: value`,
  # quotes stripped. Both quote styles are valid YAML and a leftover quote
  # would sail into the image reference, so the result is validated below.
  awk -v key="$2" -F'[:[:space:]]+' '$1 == key { gsub(/["'"'"']/, "", $2); print $2; exit }' "$1"
}

chart_name="$(scalar "${chart_yaml}" name)"
app_version="${APP_VERSION:-$(scalar "${chart_yaml}" appVersion)}"
# Not `scalar`: a repository may carry a registry port, and splitting the line
# on every colon would cut the reference in half at it.
image_repository="${IMAGE_REPOSITORY:-$(awk '/^[[:space:]]+repository:[[:space:]]/ { gsub(/["'"'"']/, "", $2); print $2; exit }' "${values_yaml}")}"

if [[ ! "${chart_name}" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
  echo "Unusable chart name read from ${chart_yaml}: '${chart_name}'" >&2
  exit 1
fi
if [[ ! "${app_version}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
  echo "Unusable appVersion: '${app_version}'" >&2
  exit 1
fi
# The OCI reference grammar: an optional host with an optional port, then
# path components. A character class alone would accept `foo/`, `foo//bar` and
# `foo/.bar`, none of which a registry can serve.
component='[a-z0-9]+(([._]|__|[-]+)[a-z0-9]+)*'
if [[ ! "${image_repository}" =~ ^${component}(:[0-9]+)?(/${component})*$ ]]; then
  echo "Unusable image repository: '${image_repository}'" >&2
  exit 1
fi

# Drop any block a previous run left behind: a retried package step would
# otherwise emit a second artifacthub.io/images key into the same Chart.yaml.
if grep -q '^  artifacthub.io/images:' "${chart_yaml}"; then
  awk '
    /^  artifacthub\.io\/images:/ { skip = 1; next }
    skip && /^    / { next }
    { skip = 0; print }
  ' "${chart_yaml}" > "${chart_yaml}.tmp"
  mv "${chart_yaml}.tmp" "${chart_yaml}"
fi

{
  echo "  artifacthub.io/images: |"
  echo "    - name: ${chart_name}"
  echo "      image: ${image_repository}:${app_version}"
} >> "${chart_yaml}"

echo "Annotated ${chart_yaml} with ${image_repository}:${app_version}"
