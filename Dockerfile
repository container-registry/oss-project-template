# Two stages: the binary is built on the host by `task release-assets` or here,
# then copied into a base image that contains nothing else.
#
# Every choice below is deliberate; see the comment above it before changing it.

ARG BASE_IMAGE=gcr.io/distroless/static-debian12:nonroot
ARG BASE_IMAGE_DIGEST=sha256:1b7b9f0f0e0a1d2155f531db587cc48ec26aaf97ab64364225f5bf18a054e66a

# --platform=$BUILDPLATFORM keeps the compiler on the native runner and lets Go
# cross-compile. Without it a linux/arm64 build runs the whole Go toolchain
# under QEMU, which is minutes slower for no benefit.
FROM --platform=$BUILDPLATFORM golang:1.27.0-alpine AS builder

WORKDIR /src

# Copy the manifests first so `go mod download` is cached independently of the
# source. go.sum is copied with a glob because a project with no external
# dependencies has none, and a missing file would fail the COPY.
COPY go.mod go.su[m] ./
RUN go mod download

COPY . .

ARG VERSION=dev
ARG TARGETOS
ARG TARGETARCH

# -trimpath strips local filesystem paths so two builds of the same commit
# produce the same binary. The version is stamped in so the binary can report
# which release it came from.
RUN CGO_ENABLED=0 GOOS=${TARGETOS:-linux} GOARCH=${TARGETARCH} \
    go build -trimpath -ldflags="-s -w -X main.version=${VERSION}" -o /out/app .

# hadolint ignore=DL3006
FROM ${BASE_IMAGE}@${BASE_IMAGE_DIGEST}

# Repeated because ARGs do not cross stage boundaries.
ARG VERSION=dev

# Consumed by tooling and by GitHub to link the image back to this repository.
LABEL org.opencontainers.image.title="{{REPO_NAME}}" \
      org.opencontainers.image.description="{{REPO_DESCRIPTION}}" \
      org.opencontainers.image.source="https://github.com/{{ORG_NAME}}/{{REPO_NAME}}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.vendor="{{COPYRIGHT_HOLDER}}"

COPY --from=builder /out/app /app

# The distroless nonroot tag already runs as 65532. Stated explicitly so it
# survives a base image change.
USER 65532:65532

ENTRYPOINT ["/app"]
