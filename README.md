# geni-uploader

Generic container image for the user-run Geni source uploader.

The image carries the pinned, reviewed `geni_upload.py`. Your own git
repository (mounted at runtime) supplies only DATA: the upload manifest,
the scanned sources, and the status file. No credentials are baked into
the image; `GITHUB_TOKEN` and `GENI_ACCESS_TOKEN` are supplied at runtime.

Run (plan mode):

    podman run --rm -e GITHUB_TOKEN -e GENI_UPLOAD_REPO=https://github.com/<you>/<repo>.git \
      -v ~/geni-upload-state:/state quay.io/reihlinstinct/geni-uploader:latest plan

See the private runbook for full usage.
