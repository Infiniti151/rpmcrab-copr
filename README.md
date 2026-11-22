# rpmcrab-copr

[![Build](https://img.shields.io/github/actions/workflow/status/Infiniti151/rpmcrab-copr/copr-build.yml?style=for-the-badge&label=build)](https://github.com/Infiniti151/rpmcrab-copr/actions)
[![COPR Build Status](https://img.shields.io/badge/dynamic/json?url=https://copr.fedorainfracloud.org/api_3/build/list/%3Fownername%3Dinfiniti151%26projectname%3Drpmcrab%26limit%3D1&query=$.items[0].state&label=COPR&style=for-the-badge&logo=fedora&logoColor=white&color=%2351A2DA)](https://copr.fedorainfracloud.org/coprs/infiniti151/rpmcrab/)
[![rpmcrab version](https://img.shields.io/github/v/tag/plusky/rpmcrab?style=for-the-badge&label=rpmcrab)](https://github.com/plusky/rpmcrab/tags)
[![Fedora Versions](https://img.shields.io/badge/Fedora-44%20%7C%2045%20%7C%20Rawhide%20%7C%20ELN-3c6eb4?style=for-the-badge&logo=fedora&logoColor=white)](https://fedoraproject.org/)
![Arch x86_64](https://img.shields.io/badge/Arch-x86__64-purple?style=for-the-badge)
[![License](https://img.shields.io/github/license/Infiniti151/rpmcrab-copr?style=for-the-badge&logo=spdx&logoColor=white&color=yellow&label=License)](https://github.com/Infiniti151/rpmcrab-copr/blob/main/LICENSE)

Fedora packaging for [rpmcrab](https://github.com/plusky/rpmcrab), a drop-in
replacement for `rpmlint` rewritten in Rust.

Upstream's release binaries are built for openSUSE and link against a different
`librpm` than Fedora ships, so on Fedora the options were building from source
or a lot of guesswork. This repo builds rpmcrab against each Fedora release's
own `librpm` and publishes the result in Copr.

**Copr project:** <https://copr.fedorainfracloud.org/coprs/infiniti151/rpmcrab/>

## Install

```bash
sudo dnf copr enable infiniti151/rpmcrab
sudo dnf install rpmcrab
```

Built for Fedora 44, Fedora 45, ELN and Rawhide (x86_64).

Check it works:

```bash
rpmcrab --version
rpmcrab -s path/to/package.spec
```

## Known noise: `no-copyright-comment` and other SUSE-only findings

rpmcrab follows openSUSE's `rpmlint` flavour by default and bundles openSUSE's
data files, so on Fedora specs it can report things that reflect SUSE
conventions. The one you will most likely see is:

```
package.spec: W: no-copyright-comment
```

It is a warning, and an error with `-s` (strict). The check passes as soon as the
spec has a comment line starting with `# Copyright` (capital C, whole word).
Fedora specs do not usually have one, and the check is built into rpmcrab's spec
check, so it is not removed by Fedora's configuration.

You can either add a `# Copyright ...` comment to the spec, or filter the message
as described below.

### Silence it for every spec you check

Put a filter in your user config. rpmcrab reads `*.toml` files from
`~/.config/rpmlint/` in addition to `/etc/xdg/rpmlint/`, so this needs no
command-line flags:

```bash
mkdir -p ~/.config/rpmlint
cat > ~/.config/rpmlint/rpmcrab.toml <<'EOF'
Filters = [
  "no-copyright-comment",
]
EOF
```

Check that it is picked up. The file should appear in the `configuration:`
list, and the summary should say `1 filtered` instead of `1 errors`:

```bash
rpmcrab -s path/to/package.spec
```

The filter applies to every package you check as that user. Delete the file to
remove it.

### Silence it for one project or in CI

Use an rpmlintrc file and pass it with `-r`. This keeps the filter in the
repository, so CI and other contributors get the same result:

```python
# rpmcrab.rpmlintrc
addFilter("no-copyright-comment")
```

```bash
rpmcrab -s -r rpmcrab.rpmlintrc path/to/package.spec
```

The rpmlintrc format is the one `rpmlint` uses, so the same file works with both
tools. If `rpmcrab` reports an `unused-rpmlintrc-filter` message for a spec that
already has a copyright header, add `--ignore-unused-rpmlintrc`.

Other SUSE-specific checks may show up depending on what you lint. Add a filter
for each one the same way, and use `rpmcrab -e <message-id>` to see what a
finding means.

## Packaging notes

- Built from the upstream tag; the spec lives in [`rpmcrab.spec`](rpmcrab.spec).
- Crates are fetched at build time, so the Copr project needs internet access
  enabled during builds.
- The package installs the `rpmcrab` binary, its man page and bash, zsh and
  fish completions.
- `file` is a hard runtime requirement. Helpers such as `binutils`,
  `desktop-file-utils`, `libappstream-glib`, `dash`, `devscripts-checkbashisms`
  and the usual compressors are `Recommends`; the checks that need them are
  skipped when they are missing.
- `rpmcrab` links against `librpm` directly, so each Fedora release needs its own
  build, and a new `rpm` soname means a rebuild.

### Build locally

```bash
mock -r fedora-45-x86_64 --enable-network --buildsrpm --spec rpmcrab.spec --sources .
mock -r fedora-45-x86_64 --enable-network --rebuild /var/lib/mock/fedora-45-x86_64/result/rpmcrab-*.src.rpm
```

## License

The packaging files in this repository (the spec file, README and scripts) are
licensed under the [MIT License](LICENSE).

`rpmcrab` itself is licensed separately, under GPL-2.0-or-later. See the
[upstream repository](https://github.com/plusky/rpmcrab).