# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.5] - 2026-09-21

Maintenance release. No user-facing feature or behaviour changes: this brings
the runtime and dependencies current after an extended gap, and resolves all
outstanding HIGH severity findings in the release image.

## Security

* Resolved every outstanding HIGH severity vulnerability reported by Trivy,
  covering pyasn1, urllib3, Flask, Werkzeug, requests, idna and Flask-HTTPAuth
  by @mshade in https://github.com/mshade/kronic/pull/176
* Removed `pip` from the release image. It is never invoked at runtime, and its
  vendored dependencies were the only remaining source of HIGH findings
  by @mshade in https://github.com/mshade/kronic/pull/174

## Changed

* Base image moved from `python:3.12-alpine` to `python:3.14-alpine`
  by @renovate in https://github.com/mshade/kronic/pull/174
* `urllib3` crossed the 1.x to 2.x major boundary (1.26.18 to 2.8.0)
* `google-auth` now requires `cryptography`, so `cryptography`, `cffi` and
  `pycparser` are pinned explicitly to keep `requirements.txt` a complete closure
* Renovate groups non-major updates into one PR per manager, and again tracks the
  Dockerfile base image, which a malformed versioning rule had silently excluded
  by @mshade in https://github.com/mshade/kronic/pull/180
* Squelched Dockerfile build warnings by @mshade in https://github.com/mshade/kronic/pull/142

## Updated

Runtime dependencies, from v0.1.4:

* blinker 1.7.0 to 1.9.0
* boltons 23.1.1 to 24.1.0
* cachetools 5.3.3 to 5.5.2
* certifi 2024.2.2 to 2024.12.14
* charset-normalizer 3.3.2 to 3.5.1
* click 8.1.7 to 8.5.0
* Flask 3.0.2 to 3.1.3
* Flask-HTTPAuth 4.8.0 to 4.8.1
* google-auth 2.28.1 to 2.58.0
* gunicorn 21.2.0 to 23.0.0
* idna 3.6 to 3.20
* itsdangerous 2.1.2 to 2.2.0
* Jinja2 3.1.3 to 3.1.6
* kubernetes 29.0.0 to 30.1.0
* oauthlib 3.2.2 to 3.3.1
* packaging 23.2 to 24.2
* pyasn1 0.5.1 to 0.6.4
* pyasn1-modules 0.3.0 to 0.4.2
* PyYAML 6.0.1 to 6.0.3
* requests 2.31.0 to 2.34.2
* requests-oauthlib 1.3.1 to 2.0.0
* rsa 4.9 to 4.9.1
* six 1.16.0 to 1.17.0
* urllib3 1.26.18 to 2.8.0
* websocket-client 1.7.0 to 1.9.2
* Werkzeug 3.0.1 to 3.1.8

Development dependencies: pytest 8.0.2 to 9.1.1, black 24.2.0 to 26.5.1.

CI tooling: helm 3.12.0 to 3.22.0, chart-testing-action 2.6.1 to 2.8.0,
kind-action 1.9.0 to 1.15.0, chart-releaser-action 1.6.0 to 1.7.0.

**Full Changelog**: https://github.com/mshade/kronic/compare/v0.1.4...v0.1.5


## [0.1.4] - 2024-03-04

## Added

* Contain logs in display by @mshade in https://github.com/mshade/kronic/pull/64
* include schedule in main display, show most recent jobs/pods first by @mshade in https://github.com/mshade/kronic/pull/63
* Handle wrapping lines without breaks by @mshade in https://github.com/mshade/kronic/pull/65
* :rocket: refactor pod filtering by job/cronjob to reduce number of ap… by @mshade in https://github.com/mshade/kronic/pull/67


## Updated

* update base image packages by @mshade in https://github.com/mshade/kronic/pull/61
* Update dependency pytest to v8.0.1 by @renovate in https://github.com/mshade/kronic/pull/59
* Update dependency google-auth to v2.28.1 by @renovate in https://github.com/mshade/kronic/pull/58
* Update helm/kind-action action to v1.9.0 by @renovate in https://github.com/mshade/kronic/pull/55
* Update dependency black to v24.2.0 by @renovate in https://github.com/mshade/kronic/pull/56
* Update dependency pytest to v8.0.2 by @renovate in https://github.com/mshade/kronic/pull/62
* Update dependency cachetools to v5.3.3 by @renovate in in https://github.com/mshade/kronic/pull/68
* Update azure/setup-helm action to v4 by @renovate in in https://github.com/mshade/kronic/pull/69
* Update dependency python-dateutil to v2.9.0.post0 by @renovate in https://github.com/mshade/kronic/pull/70

**Full Changelog**: https://github.com/mshade/kronic/compare/v0.1.3...v0.1.4


## [0.1.3] - 2024-02-07

### Added

* Update dependency kubernetes to v28 by @renovate in https://github.com/mshade/kronic/pull/19
* Update dependency black to v23.10.1 by @renovate in https://github.com/mshade/kronic/pull/30
* Update python Docker tag to v3.12 by @renovate in https://github.com/mshade/kronic/pull/27
* Update dependency Werkzeug to v3 by @renovate in https://github.com/mshade/kronic/pull/23
* Update dependency Flask to v3 by @renovate in https://github.com/mshade/kronic/pull/22
* Update dependency pytest to v7.4.3 by @renovate in https://github.com/mshade/kronic/pull/32
* Update dependency cachetools to v5.3.2 by @renovate in https://github.com/mshade/kronic/pull/31
* Update dependency websocket-client to v1.6.4 by @renovate in https://github.com/mshade/kronic/pull/29
* Update dependency blinker to v1.6.3 by @renovate in https://github.com/mshade/kronic/pull/28
* Update dependency packaging to v23.2 by @renovate in https://github.com/mshade/kronic/pull/24
* Update dependency charset-normalizer to v3.3.1 by @renovate in https://github.com/mshade/kronic/pull/21
* Update dependency google-auth to v2.23.3 by @renovate in https://github.com/mshade/kronic/pull/20
* Update dependency urllib3 to v1.26.18 [SECURITY] by @renovate in https://github.com/mshade/kronic/pull/26
* Update dependency charset-normalizer to v3.3.2 by @renovate in https://github.com/mshade/kronic/pull/36
* Update dependency Jinja2 to v3.1.3 by @renovate in https://github.com/mshade/kronic/pull/45
* Update dependency Flask to v3.0.2 by @renovate in https://github.com/mshade/kronic/pull/44
* Update dependency certifi to v2023.11.17 by @renovate in https://github.com/mshade/kronic/pull/40
* Update dependency pytest to v7.4.4 by @renovate in https://github.com/mshade/kronic/pull/47
* Update dependency MarkupSafe to v2.1.5 by @renovate in https://github.com/mshade/kronic/pull/46
* Update dependency google-auth to v2.27.0 by @renovate in https://github.com/mshade/kronic/pull/34
* Update dependency black to v23.12.1 by @renovate in https://github.com/mshade/kronic/pull/39
* Update dependency idna to v3.6 by @renovate in https://github.com/mshade/kronic/pull/42
* Update dependency pyasn1 to v0.5.1 by @renovate in https://github.com/mshade/kronic/pull/41
* Update helm/chart-releaser-action action to v1.6.0 by @renovate in https://github.com/mshade/kronic/pull/38
* Update dependency blinker to v1.7.0 by @renovate in https://github.com/mshade/kronic/pull/37
* Update dependency boltons to v23.1.1 by @renovate in https://github.com/mshade/kronic/pull/35
* Update actions/setup-python action to v5 by @renovate in https://github.com/mshade/kronic/pull/49
* Update dependency websocket-client to v1.7.0 by @renovate in https://github.com/mshade/kronic/pull/48
* Update dependency certifi to v2024 by @renovate in https://github.com/mshade/kronic/pull/52
* Update dependency black to v24 by @renovate in https://github.com/mshade/kronic/pull/51
* Update dependency kubernetes to v29 by @renovate in https://github.com/mshade/kronic/pull/53
* Update dependency pytest to v8 by @renovate in https://github.com/mshade/kronic/pull/54

**Full Changelog**: https://github.com/mshade/kronic/compare/v0.1.2...v0.1.3


## [0.1.2] - 2023-09-13

### Added

* :rocket: prepare v0.1.1 by @mshade in https://github.com/mshade/kronic/pull/17
* Feature: Built-in basic auth on backend by @mshade in https://github.com/mshade/kronic/pull/18
* Removed: ingress-based basic auth by @mshade in https://github.com/mshade/kronic/pull/18


**Full Changelog**: https://github.com/mshade/kronic/compare/v0.1.1...v0.1.2

## [0.1.1] - 2023-09-12

### Added

* :rocket: prepare v0.1.1 by @mshade in https://github.com/mshade/kronic/pull/17
* :art: some code cleanup by @mshade in https://github.com/mshade/kronic/pull/10
* Update dependency pytest to v7.4.2 by @renovate in https://github.com/mshade/kronic/pull/8
* Update dependency google-auth to v2.23.0 by @renovate in https://github.com/mshade/kronic/pull/11
* Update dependency websocket-client to v1.6.3 by @renovate in https://github.com/mshade/kronic/pull/9
* Update docker/metadata-action action to v5 by @renovate in https://github.com/mshade/kronic/pull/14
* Update docker/login-action action to v3 - autoclosed by @renovate in https://github.com/mshade/kronic/pull/13
* Update docker/build-push-action action to v5 by @renovate in https://github.com/mshade/kronic/pull/12
* Feature: namespace allowlist by @mshade in https://github.com/mshade/kronic/pull/15
* Feature: support namespaced installation by @mshade in https://github.com/mshade/kronic/pull/16


**Full Changelog**: https://github.com/mshade/kronic/compare/kronic-chart-0.1.3...v0.1.1-preview

## [0.1.0] - 2023-09-06

### Added

- Initial release! :tada:
