# localsend-fedora-copr-ci

[LocalSend](https://github.com/localsend/localsend) is an open source cross-platform alternative to AirDrop. It lets you share files and messages with nearby devices over the local network, with no external servers needed.

This repo packages LocalSend for Fedora by rewrapping the upstream prebuilt Linux DEB (`LocalSend-X.Y.Z-linux-x86-64.deb`) with a Fedora spec. Currently x86_64 only, matching the tested prebuilt release artifact (upstream also ships an arm-64 DEB). A GitHub Actions workflow runs daily at 12AM UTC to check the latest release from https://github.com/localsend/localsend and rebuilds COPR only when a new version is published. The downloaded DEB is verified against a recorded SHA256 checksum before submission.

The COPR project repository is available from: https://copr.fedorainfracloud.org/coprs/anudeepd/localsend

## Packaging compliance

This package is distributed via COPR only. It rewraps the upstream prebuilt
binary DEB, so it is **not eligible for the official Fedora repositories**:
the Fedora Packaging Guidelines require all binaries to be built from source
in the Fedora build system, and this repo intentionally ships the upstream
blob as-is (see `specs/localsend.spec`).

Everything else follows the guidelines:

- `ExclusiveArch: x86_64` — matches the tested upstream prebuilt artifact.
- `%build` present (empty — nothing to compile) so rpm's build hooks run.
- `%check` runs `desktop-file-validate` and `appstreamcli validate` on the
  packaged files inside the build.
- `rpmlint` runs in CI on the built RPM with **0 errors, 0 warnings**:
  every flagged pattern is inherent to rewrapping the Flutter blob
  (the `/opt` layout, required `$ORIGIN` runpaths, bare SONAMEs on the
  private libs, unstripped prebuilt binaries, dictionary misses, GUI app
  without man page, docs not bundled by design) and is filtered
  in `rpmlintrc` with per-filter rationales.
- `%{_bindir}`, `%{_datadir}`, `%{_metainfodir}` macros used in `%files`.
- License provenance: the Apache-2.0 license text is fetched from the upstream
  release tag by `spectool` (the prebuilt DEB ships none); a fetch failure
  fails the build, so the packaged license always matches the packaged
  version. `License: Apache-2.0` (SPDX) matches the upstream `LICENSE`.
  Nothing else is bundled: upstream payload plus license and curated metainfo.
- `%global debug_package %{nil}` with an explicit rationale: the prebuilt
  foreign binary cannot produce debuginfo, so the debug package is meaningless
  for a rewrap. Note that this is what *enables* Fedora's ELF-rewriting brp
  hooks rather than skipping them: `%__os_install_post` gates `brp-strip` and
  `brp-strip-comment-note` on `%__debug_package` being undefined, and with
  them active every ELF in the payload loses its `.comment` section.
  `brp-strip-lto` and `brp-strip-static-archive` are not gated at all. All
  four hooks plus `add-det` are emptied in the spec, so the only remaining
  difference from the upstream DEB is the documented chrpath delta — and the
  RPM build test workflow checks exactly that against the upstream payload.
- The bundled Flutter libs under `/opt/localsend_app` carry bare SONAMEs
  (e.g. `libflutter_linux_gtk.so`). These are private names nothing in
  Fedora provides, so they stay provided by this package itself, satisfying
  the package's own `DT_NEEDED` requires on them (same approach as the
  enteauth rewrap). One auto-detected dep is excluded: `libjvm.so` (via the
  unused `libdartjni.so` JNI bridge) would drag in a full JVM that upstream
  itself doesn't require.
- One minimal, documented transformation: upstream's Flutter plugin libs
  bake in a `RUNPATH` pointing at the GitHub Actions build workspace
  (`/home/runner/work/...`) plus the Debian multiarch dir, neither of which
  exists on Fedora, failing `check-rpaths`. `%prep` deletes the `RUNPATH`
  with `chrpath` on exactly the affected files (a no-op if upstream ever
  stops emitting it); code and the working `$ORIGIN` runpath on the main
  binary are untouched.
- A second minimal, documented transformation: upstream's `postinst` symlinks
  `/opt/localsend_app/localsend_app` to `/usr/bin` via a shell script; the
  spec declares the same link in `%install` instead, so rpm owns it and no
  scriptlet is needed. The blob itself is untouched.
- Upstream ships no AppStream metadata at all, so this repo ships a curated
  `org.localsend.localsend_app.metainfo.xml` (RDNS id following Flathub's,
  launchable pointing at the upstream desktop file); the upstream desktop
  file and icons are kept as-is.
- Dependencies: everything the blob links (gtk3, ayatana tray libs,
  dbusmenu, epoxy, fontconfig, …) is auto-detected from `DT_NEEDED`.
  Explicitly listed are only what the generator cannot see:
  `hicolor-icon-theme` (hicolor icons), `xdg-user-dirs` (used by the
  open_dir plugin at runtime, declared by the upstream DEB too) and
  `xdg-utils` (the url_launcher plugin shells out to `xdg-open`).
  Deliberately not mirrored from upstream: the legacy `libappindicator`
  compat alternative (the tray plugin links ayatana). No network access
  inside the buildroot.
- The downloaded DEB is verified against a recorded SHA256 checksum before
  submission to COPR. Note this is trust-on-first-use (guards
  corruption/mismatch, not a signing boundary): upstream publishes no
  checksums or signatures for the DEB.

# Instructions

Enable the COPR repository then install the package.

<pre>
sudo dnf copr enable anudeepd/localsend
sudo dnf install localsend
</pre>

## Credits

Pattern and workflow structure adapted from
[anudeepd/ente-auth-fedora-copr-ci](https://github.com/anudeepd/ente-auth-fedora-copr-ci)
(which itself was adapted from
[anudeepd/iloader-fedora-copr-ci](https://github.com/anudeepd/iloader-fedora-copr-ci),
in turn adapted from
[DeltaCopy/waterfox-fedora-copr-ci](https://github.com/DeltaCopy/waterfox-fedora-copr-ci))
— thanks for the clean reference implementation.

<h3> COPR build status </h3>

[![Copr build status](https://copr.fedorainfracloud.org/coprs/anudeepd/localsend/package/localsend/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/anudeepd/localsend/package/localsend/)

<h3> GitHub action workflow status </h3>

[![localsend Fedora COPR CI](https://github.com/anudeepd/localsend-fedora-copr-ci/actions/workflows/localsend-ci.yml/badge.svg)](https://github.com/anudeepd/localsend-fedora-copr-ci/actions/workflows/localsend-ci.yml)

## Latest version
<a href="https://github.com/localsend/localsend/releases">
  <img src="https://img.shields.io/github/v/release/localsend/localsend" alt="localsend latest release">
</a>
