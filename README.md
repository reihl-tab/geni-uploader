# geni-uploader

Generic container image for the user-run Geni source uploader.

The image carries the pinned, reviewed `geni_upload.py`. Your own git
repository (cloned at runtime into a tmpfs) supplies only DATA: the upload
manifest, the scanned sources, and the status file. No credentials are
baked into the image; they are mounted at runtime:

- a read/write GitHub token as a file at `/run/gh-token` (mode 600),
- a Geni access token passed via `--token-file /run/geni-token`
  (or the `GENI_ACCESS_TOKEN` environment variable).

Run (plan mode, no writes):

    podman run --rm --tmpfs /work \
      -e GENI_UPLOAD_REPO=https://github.com/<you>/<repo>.git \
      -v ~/.gh-token:/run/gh-token:ro,Z \
      -v ~/.geni-token:/run/geni-token:ro,Z \
      quay.io/reihlinstinct/geni-uploader:latest \
      --token-file /run/geni-token plan \
      --manifest path/to/upload-manifest.yaml

See the private runbook for full usage.
