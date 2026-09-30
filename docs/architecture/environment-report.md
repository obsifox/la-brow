# Environment Report

Collected at 2026-09-30T14:47:27Z. The report contains factual measurements only.

## Operating System

- system: Linux
- release: 6.1.158+
- distribution: Debian GNU/Linux 13 (trixie)
- libc: ('glibc', '2.41')

## Architecture

- machine: x86_64
- pointer bits: 64

## CPU

- model: Intel(R) Xeon(R) Processor @ 2.60GHz
- logical cores: 2

## Memory

- total: 2032608 kB
- available: 1529980 kB
- swap total: 0 kB

## Storage

- /: free 21203406848 bytes of 25860014080 bytes, used 16.8 percent
- /home/user: free 21203406848 bytes of 25860014080 bytes, used 16.8 percent
- /tmp: free 1039011840 bytes of 1040695296 bytes, used 0.2 percent

## Graphics

- measurable: False
- detail: glxinfo is not installed; graphics stack not measurable in this environment

## Containers and Virtualization

- docker_socket: False
- podman_socket: False
- cgroup_v2: True
- kvm_device: False

## Toolchain

| Tool | Present | Version Line |
| --- | --- | --- |
| gcc | True | gcc (Debian 14.2.0-19) 14.2.0 |
| g++ | True | g++ (Debian 14.2.0-19) 14.2.0 |
| clang | False | not available |
| rustc | False | not available |
| cargo | False | not available |
| python3 | True | Python 3.13.14 |
| node | True | v20.20.2 |
| java | True | openjdk version "11" 2018-09-25 |
| gradle | False | not available |
| cmake | False | not available |
| ninja | False | not available |
| make | True | GNU Make 4.4.1 |
| git | True | git version 2.47.3 |
| hg | True | Mercurial Distributed SCM (version 7.0.1) |
| openssl | True | OpenSSL 3.5.6 7 Apr 2026 (Library: OpenSSL 3.5.6 7 Apr 2026) |
| docker | False | not available |
| podman | False | not available |
| qemu-system-x86_64 | False | not available |

## Python Modules

- pytest: 9.0.3
- yaml: 6.0.3
- jsonschema: 4.26.0
- PIL: 12.3.0
- cryptography: not installed

## Android Toolchain

- environment variables present: {'ANDROID_HOME': False, 'ANDROID_SDK_ROOT': False, 'ANDROID_NDK_ROOT': False, 'JAVA_HOME': False}

## Consequences For This Project

Recorded facts that constrain the engineering plan:

- Rust is not available, so any Gecko build step that requires the Rust toolchain cannot run in this environment.
- Clang is not available, so the recommended Gecko compiler toolchain cannot run in this environment.
- CMake and Ninja are not available, so the Gecko build system cannot run in this environment.
- Gradle is not installed, so the Android application cannot be assembled in this environment.
- No Android SDK is configured, so Android packaging remains a validated scaffold rather than a built artifact.
- No container runtime is available, so build isolation must be documented for a capable build host.
- The environment core, policy scanners and test suite run fully in this environment.
