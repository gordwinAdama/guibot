#!/bin/bash
set -e

# This is an explicit script for PyPI installations reusing the current Travis
# CI configuration in the format of our platform-specifric packager scripts.

readonly distro="${DISTRO:-centos}"
readonly distro_version="${VERSION:-8}"
readonly distro_root="${ROOT:-$HOME}"
readonly python_version="${PYTHON_VERSION:-3.8}"
readonly release_tag="${RELEASE_TAG:-}"

# disable tests and support of backends based on python versions
if [[ $python_version == '3.9' ]]; then export DISABLE_AUTOPY=1; fi

# environment dependencies not provided by pip
# python3

if [[ $python_version == '3.9' ]]; then dnf -y install python39 python39-devel; fi
if [[ $python_version == '3.8' ]]; then dnf -y install python38 python38-devel; fi
if [[ $python_version == '3.7' ]]; then dnf -y install python37 python37-devel; fi
if [[ $python_version == '3.6' ]]; then dnf -y install python36 python36-devel; fi
alternatives --install /usr/bin/python3 python3 /usr/bin/python${python_version} 60 \
             --slave /usr/bin/pip3 pip3 /usr/bin/pip${python_version}
alternatives --set python3 /usr/bin/python${python_version}
# pip dependencies in order to build some PyPI packages
dnf -y install gcc libX11-devel libXtst-devel libpng-devel redhat-rpm-config
# text matching
dnf -y install tesseract tesseract-devel
dnf -y install gcc-c++
# screen controlling
dnf -y install xdotool xwd ImageMagick
# TODO: PyAutoGUI's scrot dependencies are broken on CentOS/Rocky, currently provided offline
#dnf -y install scrot
dnf -y install x11vnc

# dependencies that could be installed using pip
pip3 install --upgrade pip
pip3 install -r "$distro_root/guibot/packaging/pip_requirements.txt"

# auto-review and linters
cd "$distro_root/guibot"
echo "Performing auto-review linting checks on code and documentation"
pycodestyle guibot/* --ignore="E501,W503,E226,E265,E731,E306"
pydocstyle guibot/* --ignore="D212,D205,D400,D401,D415,D203,D105,D301,D302"

# pip packaging and installing of current guibot source
pip3 install wheel twine
cd "$distro_root/guibot/packaging"
python3 setup.py sdist bdist_wheel
pip3 install dist/guibot*.whl

# virtual display
dnf install -y xorg-x11-server-Xvfb vim-common
export DISPLAY=:99.0
Xvfb :99 -screen 0 1024x768x24 &> /tmp/xvfb.log  &
touch /root/.Xauthority
xauth add ${HOST}:99 . $(xxd -l 16 -p /dev/urandom)
sleep 3  # give xvfb some time to start

# unit tests
# the tests and misc data are not included in the PIP package
cp -r "$distro_root/guibot/tests" /usr/local/lib/python3*/site-packages/guibot/
cp -r "$distro_root/guibot/misc" /usr/local/lib/python3*/site-packages/guibot/
cd /usr/local/lib/python3*/site-packages/guibot/tests
if (( distro_version <= 7 )); then
    COVERAGE="python3-coverage"
else
    COVERAGE="coverage-${python_version}"
fi
LIBPATH=".." COVERAGE="$COVERAGE" sh coverage_analysis.sh
# TODO: need supported git provider (e.g. GH actions web hooks) for codecov submissions
#mv "$distro_root/guibot/.git" /usr/local/lib/python3*/site-packages/guibot/
#LIBPATH=".." COVERAGE="$COVERAGE" SUBMIT=1 sh coverage_analysis.sh

if [[ -n "$release_tag" ]]; then
    echo "Releasing version ${release_tag} to PyPI"
    cd "$distro_root/guibot/packaging"
    if [[ -z $USER ]]; then echo "No username provided as an environment variable" && exit 1; fi
    if [[ -z $PASS ]]; then echo "No password provided as an environment variable" && exit 1; fi
    git_tag="$(git describe)"
    if [[ "$release_tag" != "$git_tag" ]]; then
        echo "Selected release version ${release_tag} does not match tag ${git_tag}"
        exit 1
    fi
    twine upload --repository pypi --user "$USER" --password "$PASS" dist/*
fi

exit 0
