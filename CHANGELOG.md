# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive README with architecture diagram, CLI documentation, and usage examples
- ARCHITECTURE.md with detailed design and data flow documentation
- CHANGELOG.md

## [1.0.0]

### Added
- Containerized Geni source uploader (`geni_upload.py`)
- Support for uploading documents and photos to Geni profiles via manifest
- Durable resume capability with journaled upload protocol and status file tracking
- CLI commands: `auth-url`, `whoami`, `plan`, `run`, `contrast`, `guidmap`, `pguid`
- Manifest schema with `targets`, `profile_id`, `expect_name`, `documents`, `photos`, `also_tag`
- GUID resolution for profile URLs to API identifiers (docs/guid-resolution.md)
- GitHub Actions workflows for CI and image publishing
- Comprehensive documentation in `docs/` directory (usage, DURABLE_RESUME, guid-resolution, privacy, geni-token, source-details-design, profile-creation-design, index)
- Privacy and security documentation (PRIVACY.md, SECURITY.md, docs/privacy.md)

### Design Documentation (no implementation)
- Profile creation design (docs/profile-creation-design.md) — design phase, issue #68
- Existing-source metadata repair design (docs/source-details-design.md) — user-only, pending image release

### Security
- Read-only credential mounts (no credentials baked into image)
- Ephemeral tmpfs workspace (no disk persistence)
- No execution of user repository code
- Git credential helper scoped to github.com only
- Allowlisted API calls enforcing permitted (method, kind) pairs
