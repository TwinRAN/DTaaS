# TwinRAN - a DT-enabled AI optimization for 6G

<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [System Setup (Rocky 9)](#system-setup-rocky-9)
   * [Install Docker CE](#install-docker-ce)
   * [SCTP](#sctp)
- [Clone all the projects](#clone-all-the-projects)
- [Local Development/Build/Run of an xApp (Complex Configuration)](#local-developmentbuildrun-of-an-xapp-complex-configuration)
   * [Install Python 3.10 for FlexRIC](#install-python-310-for-flexric)
   * [Install FlexRIC build requirements](#install-flexric-build-requirements)
   * [Install Compiler Cache](#install-compiler-cache)
   * [Install GCC13](#install-gcc13)
   * [Install libraries for the xApp](#install-libraries-for-the-xapp)
   * [Install Language Server](#install-language-server)
   * [Build and Run FlexRIC with xApp](#build-and-run-flexric-with-xapp)
- [Containerized Development/Build/Run (Simple Configuration)](#containerized-developmentbuildrun-simple-configuration)

<!-- TOC end -->

<!-- TOC --><a name="system-setup-rocky-9"></a>
## System Setup (Rocky 9)

<!-- TOC --><a name="install-docker-ce"></a>
### Install Docker CE

```sh
dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
dnf install docker-ce docker-ce-cli containerd.io
systemctl enable --now docker
```

<!-- TOC --><a name="sctp"></a>
### SCTP
Install and setup SCTP using the following guide [https://access.redhat.com/solutions/6625041](https://access.redhat.com/solutions/6625041)

```sh
dnf install kernel-modules-extra-`uname -r` # 
```

Enable SCTP as it is disabled upon install by default due to security concerns [https://access.redhat.com/articles/3760101](https://access.redhat.com/articles/3760101). Using your text editor (e.g. `vim` or `nano`) comment out the following lines in these two files.

```sh
$ grep sctp /etc/modprobe.d/*
/etc/modprobe.d/sctp-blacklist.conf:#blacklist sctp
/etc/modprobe.d/sctp_diag-blacklist.conf:#blacklist sctp_diag
```

Enable auto-loading of SCTP by adding `sctp` into `/etc/modules-load.d/sctp.conf` file you create using your text editor.

```sh
cat /etc/modules-load.d/sctp.conf
sctp
```

Restart the system and confirm the module is loaded
```sh
reboot
lsmod | grep sctp
sctp                  544768  4
ip6_udp_tunnel         16384  1 sctp
udp_tunnel             36864  1 sctp
libcrc32c              12288  5 nf_conntrack,nf_nat,nf_tables,xfs,sctp
```

<!-- TOC --><a name="clone-all-the-projects"></a>
## Clone all the projects and run RAN and Core Networks

TwinRAN is an application that runs on openairinterface and interacts with a Radio Access Network (RAN) Intelligent Controller (RIC) called FlexRIC.

Setup openairinterface.

```sh
git clone git@gitlab.btsgrp.com:khayal.huseynov/openairinterface5g.git
cd openairinterface5g && git checkout twinran
cd ci-scripts/yaml_files/bts/
./setup.sh # executes services in docker-compose.yml step-by-step
cd - && cd ..
```

Setup Flexric project for further xApp development

```sh
git clone git@gitlab.btsgrp.com:khayal.huseynov/flexric.git
cd flexric && git checkout twinran && cd ..
```

Setup TwinRAN and run everything except `xapp_kpm_twinran`

```sh
git clone git@gitlab.btsgrp.com:khayal.huseynov/twinran.git
cd twinran
docker compose up -d $(docker compose config --services | grep -v xapp_kpm_twinran)
cd ..
```

<!-- TOC --><a name="local-developmentbuildrun-of-an-xapp-complex-configuration"></a>
## Local Development/Build of an xApp (Complex Configuration)

This part is only necessary if you want to get IDE functionalities (syntax highlighting etc.) in your development environment. It is highly recommended to create a Virtual Machine to run these commands as they will install a lot of system-level packages.

<!-- TOC --><a name="install-python-310-for-flexric"></a>
### Install Python 3.10 for FlexRIC

Install and use `pyenv` to install python3.10

```sh
dnf install -y make gcc patch zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel xz-devel libuuid-devel gdbm-libs libnsl2
curl -fsSL https://pyenv.run | bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init - bash)"' >> ~/.bashrc
tail ~/.bashrc
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.profile
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.profile
echo 'eval "$(pyenv init - bash)"' >> ~/.profile
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
echo 'eval "$(pyenv init - bash)"' >> ~/.bash_profile
echo $BASH_ENV
exec "$SHELL"
pyenv install 3.10
```

<!-- TOC --><a name="install-flexric-build-requirements"></a>
### Install FlexRIC build requirements

Install the requirements

```sh
dnf install -y lksctp-tools-devel cmake ncurses-devel pcre2-devel
```

Install swig-4.1.1 for Multi-language xApp requirements

```sh
dnf --enablerepo=crb install swig-4.1.1-1.module+el9.2.0+14720+e7fbdcea.x86_64.rpm
```

Install ASN.1 Compiler as the encoding scheme. Here, alternatively, flatcc could be used.

```sh
dnf install libtool flex bison
git clone https://github.com/vlm/asn1c.git
cd asn1c
test -f configure || autoreconf -iv
./configure --prefix /opt/asn1c
make
make install

export 'PATH="$PATH:/opt/asn1c/bin/"' >> ~/.bashrc
export 'PATH="$PATH:/opt/asn1c/bin/"' >> ~/.profile
export 'PATH="$PATH:/opt/asn1c/bin/"' >> ~/.bash_profile
cd ..
```

<!-- TOC --><a name="install-compiler-cache"></a>
### Install Compiler Cache

This is for caching cmake build layers to allow incremental builds

```sh
dnf install -y epel-release
dnf install -y ccache
```

<!-- TOC --><a name="install-gcc13"></a>
### Install GCC13

FlexRIC does not work with `gcc11` which is the Fedora/RHEL/Rocky default version currently. So we install `gcc13` and enable during bash shell initialisation

```sh
dnf install -y gcc-toolset-13
scl enable gcc-toolset-13 bash
```

<!-- TOC --><a name="install-libraries-for-the-xapp"></a>
### Install libraries for the xApp

This custom xApp for TwinRAN needs a library for Kafka connection

```sh
dnf --enablerepo=devel install -y librdkafka-devel
```

<!-- TOC --><a name="install-language-server"></a>
### Install Language Server

This is to enable LLDB in VSCode

```sh
dnf install -y clangd
```

<!-- TOC --><a name="build-and-run-flexric-with-xapp"></a>
### Build and Run FlexRIC with xApp

Build FlexRIC with our custom xApp

```sh
cd flexric
rm -rf build && mkdir build && cd build && cmake -DASN1C_EXEC_PATH=/opt/asn1c/bin/asn1c -DE2AP_VERSION=E2AP_V3 -DKPM_VERSION=KPM_V3_00 .. && make -j$(nproc) VERBOSE=1 2>&1 | tee build.log
make install
cd ..
```

To run the application in your shell, execute the following

```sh
flexric/examples/xApp/c/monitor/xapp_kpm_kafka -p /usr/local/lib64/flexric/ # default looks at lib instead of lib64
```

<!-- TOC --><a name="containerized-developmentbuildrun-simple-configuration"></a>
## Containerized Development (Simple Configuration)

After code changes to TwinRAN, just run the following

```sh
cd twinran
docker build -f docker/Dockerfile.flexric.ubuntu -t xapp_kpm_twinran_ubuntu:latest . --progress=plain 2>&1 | tee build.log
cd ..
```

Restart `xapp_kpm_twinran`

```sh
cd twinran
docker compose up -d xapp_kpm_twinran
cd ..
```
