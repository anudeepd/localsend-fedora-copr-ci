# Prebuilt foreign binary: no build-id or debuginfo can be produced, so the
# debug package is disabled. The payload ships as-is from the release DEB.
%global debug_package %{nil}

# NOTE (verified by local rpmbuild): %%global debug_package %%{nil} is what
# makes the default ELF-rewriting brp hooks run, not what skips them —
# Fedora's %%__os_install_post gates brp-strip / brp-strip-comment-note on
# %%__debug_package being *undefined*. With them in place every ELF file in
# the payload loses its .comment section, so the payload stops matching
# upstream outside the documented chrpath delta below. brp-strip-lto and
# brp-strip-static-archive are not gated at all. Empty all four so the only
# remaining difference from the upstream DEB is the intended one. Set them to
# %%{nil} rather than %%undefine'ing them: with rpm 6.0.2 %%undefine does not
# mask brp-strip / brp-strip-comment-note (verified — the hooks still ran,
# while %%undefine on the lto one did take effect).
%global __brp_strip %{nil}
%global __brp_strip_comment_note %{nil}
%global __brp_strip_lto %{nil}
%global __brp_strip_static_archive %{nil}

# add-determinism's brp hook (add-det) would regenerate /usr/lib/.build-id
# links from the payload's ELF build-id notes and otherwise normalize the
# payload. The payload must ship byte-identical apart from the chrpath delta,
# so unset the hook.
%undefine __brp_add_determinism

# The bundled Flutter libs under /opt/localsend_app carry bare SONAMEs
# (e.g. libflutter_linux_gtk.so). Unlike system-soname bundles, these are
# private names nothing in Fedora provides, so they stay provided by this
# package itself — satisfying the package's own DT_NEEDED requires on them
# (same approach as the enteauth rewrap). No __provides_exclude_from.
# libdartjni.so (an Android JNI bridge that Flutter bundles into every Linux
# build, and which the main binary does not link) would otherwise pull a
# libjvm.so requirement, dragging in a full JVM. Upstream's own DEB declares
# no such requirement and runs fine without it, so exclude it to keep the
# install footprint at parity.
%global __requires_exclude ^libjvm\\.so

Name:           localsend
Version:        1.18.2
Release:        %autorelease
Summary:        An open source cross-platform alternative to AirDrop
License:        Apache-2.0
URL:            https://github.com/localsend/localsend
ExclusiveArch:  x86_64

# Upstream publishes no RPM, only a DEB / tarball / AppImage per platform.
# The DEB is rewrapped: its data.tar.zst payload (minus the ar container) is
# byte-identical to the published tarball (verified for 1.18.2), and it
# additionally carries the desktop file and icons, so it is the single source.
# NOTE: the DEB reports its own version as %%{version}+<flutter build number>
# (e.g. 1.18.2+64); the RPM Version tracks the release tag without the build
# number suffix.
Source0:        https://github.com/localsend/localsend/releases/download/v%{version}/LocalSend-%{version}-linux-x86-64.deb
# Upstream prebuilt DEB ships no license file. spectool fetches LICENSE for
# the exact version being packaged from the release tag; a failed fetch fails
# the build, so the packaged license always matches the packaged version.
Source1:        https://raw.githubusercontent.com/localsend/localsend/v%{version}/LICENSE
# Curated AppStream metadata: upstream ships none (neither the DEB nor the
# tarball). The id follows Flathub's org.localsend.localsend_app; the
# launchable points at the upstream desktop file, which is kept as-is.
# CI patches the <release> version/date on each new upstream release.
Source2:        org.localsend.localsend_app.metainfo.xml

BuildRequires:  desktop-file-utils
BuildRequires:  appstream
BuildRequires:  binutils
BuildRequires:  zstd
BuildRequires:  chrpath

# Runtime-only deps the ELF dependency generator cannot see. Everything
# linked (gtk3, ayatana tray libs, dbusmenu, epoxy, fontconfig, ...) is
# auto-detected from DT_NEEDED and deliberately not duplicated here:
# - hicolor-icon-theme: the hicolor icons under /usr/share/icons need it.
# - xdg-user-dirs: declared by the upstream DEB; used by the open_dir plugin
#   at runtime (no ELF links it, so the generator cannot see it).
# - xdg-utils: the url_launcher plugin shells out to xdg-open at runtime.
# Deliberately NOT mirrored from the upstream DEB's declared requirements:
# libappindicator3-1 | libayatana-appindicator3-1 and friends (the tray
# plugin actually links the auto-detected libayatana-appindicator3).
Requires:       hicolor-icon-theme
Requires:       xdg-user-dirs
Requires:       xdg-utils

%description
LocalSend is an open source cross-platform alternative to AirDrop. It lets
you share files and messages with nearby devices over the local network,
with no external servers needed. This package rewraps the upstream prebuilt
Linux DEB for Fedora (COPR only).

%prep
# Unpack only the data payload of the DEB (control.tar.zst with its
# postinst/postrm symlink handling is intentionally ignored; the /usr/bin
# symlink is declared in %%install instead). The payload extracts to
# ./opt/localsend_app and ./usr/share/... with a leading ./ prefix.
ar p %{SOURCE0} data.tar.zst | tar -I zstd -x
# Upstream's Flutter plugin libs carry a RUNPATH pointing at the GitHub
# Actions build workspace (/home/runner/work/.../flutter/ephemeral) plus the
# Debian multiarch dir (/usr/lib/x86_64-linux-gnu), neither of which exists
# on Fedora — tripping Fedora's check-rpaths (ERROR 0002, failing %%install).
# Delete the RUNPATH with chrpath on exactly the affected files; runtime
# behavior is identical (the loader already falls back to the main binary's
# $ORIGIN/lib RUNPATH plus the system paths). This loop is a no-op if a
# future upstream release stops baking the path in.
for lib in opt/localsend_app/lib/*.so; do
  if readelf -d "$lib" 2>/dev/null | grep -q '/home/runner/work/'; then
    chrpath -d "$lib"
  fi
done
cp %{SOURCE1} LICENSE

%build
# Nothing to compile: the prebuilt upstream payload is unpacked in %%prep.
# The section exists so rpm's build hooks (e.g. macro-injected steps) run.

%install
cp -a opt %{buildroot}/
cp -a usr %{buildroot}/
install -Dm0644 %{SOURCE2} %{buildroot}%{_metainfodir}/org.localsend.localsend_app.metainfo.xml
# Upstream's postinst symlinks /opt/localsend_app/localsend_app to /usr/bin
# via a shell script. Declare the same link here instead, so rpm owns it and
# no scriptlet is needed. The blob itself is untouched.
install -d %{buildroot}%{_bindir}
ln -s /opt/localsend_app/localsend_app %{buildroot}%{_bindir}/localsend_app

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/localsend_app.desktop
appstreamcli validate --no-net %{buildroot}%{_metainfodir}/org.localsend.localsend_app.metainfo.xml

%files
%license LICENSE
%{_bindir}/localsend_app
/opt/localsend_app/
%{_datadir}/applications/localsend_app.desktop
%{_datadir}/icons/hicolor/*/apps/localsend_app.png
%{_metainfodir}/org.localsend.localsend_app.metainfo.xml
# Release is %%autorelease. COPR builds this repo from an uploaded SRPM, where
# rpm's plain %%autorelease fallback applies: the release is a literal 1 plus
# the chroot's dist tag, NOT the changelog entry count (verified against the
# published builds: iloader's 2.3.3-1 was built from a spec with three
# changelog entries, and the only unique NVRs any of these projects ever
# published came from the CI's force_build path). A %%changelog entry therefore
# documents a spec change but does not on its own give an already-built
# upstream version a new NVR — publish it with the force_build workflow input,
# which rewrites Release to %%{autorelease}.f<run_id> (a unique, higher
# release), exactly as the earlier forced builds in these projects did.

%changelog
* Sat Sep 12 2026 Anudeep D <anudeepd2@gmail.com> - 1.18.2-2
- Keep the payload matching upstream apart from the chrpath delta: unset
  Fedora's ELF-rewriting brp hooks (brp-strip, brp-strip-comment-note,
  brp-strip-lto, brp-strip-static-archive) which drop .comment from every
  bundled binary
* Fri Sep 11 2026 Anudeep D <anudeepd2@gmail.com> - 1.18.2-1
- Initial Fedora repackaging of upstream prebuilt DEB
