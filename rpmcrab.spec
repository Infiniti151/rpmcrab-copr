# zstd-sys compiles bundled C with the cc crate, which picks up RPM's CFLAGS.
# Fedora's -flto=auto -ffat-lto-objects there can leave symbols undefined at
# the final Rust link, so drop the C LTO flags for this package.
%global         _lto_cflags   %{nil}

%global         forgeurl      https://github.com/plusky/rpmcrab
%global         tag           v%{version}

Name:           rpmcrab
Version:        0.4.4
Release:        1%{?dist}
Summary:        Drop-in replacement for rpmlint, rewritten in Rust
License:        GPL-2.0-or-later AND LGPL-2.0-or-later AND MPL-2.0 AND MIT AND Apache-2.0 AND BSD-3-Clause AND BSD-2-Clause AND BSL-1.0 AND bzip2-1.0.6 AND Unicode-3.0 AND Zlib
BugURL:         https://github.com/Infiniti151/rpmcrab-copr/issues

%forgemeta

URL:            %{forgeurl}
Source0:        %{forgesource}

BuildRequires:  cargo-rpm-macros
BuildRequires:  forge-srpm-macros
BuildRequires:  gcc
BuildRequires:  clang-devel
BuildRequires:  pkgconfig(rpm)

Requires:       file
# Optional helper tools that individual checks probe for and skip when absent
Recommends:     binutils
Recommends:     desktop-file-utils
Recommends:     libappstream-glib
Recommends:     dash
Recommends:     devscripts-checkbashisms
Recommends:     rpm
Recommends:     gzip
Recommends:     bzip2
Recommends:     xz
Recommends:     zstd

%description
rpmcrab is a Rust rewrite of rpmlint, the RPM package linter. It aims to keep
rpmlint's output and exit-code contract while tightening checks to reduce false
positives.

Note: upstream targets openSUSE by default, so some findings come from SUSE
policy and may not apply to Fedora packages.

%prep
%forgesetup
%cargo_prep -N

%build
# bindgen (librpm-sys) needs the compiler builtin headers such as stddef.h
export BINDGEN_EXTRA_CLANG_ARGS="-I$(gcc -print-file-name=include)"
export CARGO_NET_OFFLINE=false
%cargo_build
env CARGO_HOME=.cargo cargo tree -e normal --prefix none --format '{p}: {l}' | sed -E 's/ \(\*\)$//; s/ \(\/[^)]*\)//' | sort -u > LICENSE.dependencies

%install
install -Dpm0755 target/rpm/%{name} %{buildroot}%{_bindir}/%{name}
install -Dpm0644 crates/%{name}/man/%{name}.1 %{buildroot}%{_mandir}/man1/%{name}.1
install -Dpm0644 crates/%{name}/completions/%{name}.bash \
    %{buildroot}%{_datadir}/bash-completion/completions/%{name}
install -Dpm0644 crates/%{name}/completions/%{name}.zsh \
    %{buildroot}%{_datadir}/zsh/site-functions/_%{name}
install -Dpm0644 crates/%{name}/completions/%{name}.fish \
    %{buildroot}%{_datadir}/fish/vendor_completions.d/%{name}.fish

%check
%{buildroot}%{_bindir}/%{name} --version

%files
%license LICENSE LICENSE.dependencies
%doc README.md SECURITY.md
%{_bindir}/%{name}
%{_mandir}/man1/%{name}.1*
%{_datadir}/bash-completion/completions/%{name}
%{_datadir}/zsh/site-functions/_%{name}
%{_datadir}/fish/vendor_completions.d/%{name}.fish

%changelog
* Sat Nov 28 2026 Infiniti151 <43163551+Infiniti151@users.noreply.github.com> - 0.4.4-1
- ci(release): run the release on ubuntu-26.04, rebuild the baseline from source

* Sun Nov 22 2026 Infiniti151 <43163551+Infiniti151@users.noreply.github.com> - 0.4.2-1
- chore(release): bump to 0.4.2 for post-release development by @plusky in #1470
- Nit batch: #1462, #1464, #1467, #1468 follow-ups by @scarabeusiv in #1472
- OCR expansion findings across the repo by @scarabeusiv in #1469
- spellcheck: skip function references with empty parens by @scarabeusiv in #1478
- files: exempt .dwz directory entries from hidden-file-or-dir by @scarabeusiv in #1479
- binaries: system fallback for undefined symbols in multi-contributor invocations by @scarabeusiv in #1480
- TagsCheck: credit sibling program names in spelling-error by @scarabeusiv in #1482
- Nit batch: #1471, #1473, #1474, #1483, #1484, #1485, #1486 follow-ups by @scarabeusiv in #1487
- Add shlib-policy-wrong-library-version (E) and deprecated-rc-symlink (W) by @scarabeusiv in #1489
- Add missing-sysusers-provider (W), changelog-not-in-sequence (E), no-%%changelog-section (E), no-copyright-comment (W) and patch-not-defined (W) by @scarabeusiv in #1491
- ... (see upstream for full release notes)
