FROM ghcr.io/tale/headplane@sha256:b053a0a6699d0a67be3f0d9bae8e7dbe35ed67ae8448412adcbad7ea49866faa
LABEL org.opencontainers.image.title="Headplane 0.8.2 Simplified Chinese"
LABEL org.opencontainers.image.description="Local UI translation of the pinned official release"
COPY build /app/build
