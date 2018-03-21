#!/bin/bash
set -e

# rpm dependencies
# python2.7
dnf -y install python
# python-imaging
dnf -y install python-pillow
# contour, template, feature, cascade, text matching
dnf -y install python2-numpy opencv-python
# text matching
dnf -y install tesseract

# pip dependencies (not available as RPM)
dnf -y install gcc libX11-devel libXtst-devel python-devel libpng-devel redhat-rpm-config
pip install autopy
pip install http://download.pytorch.org/whl/cu75/torch-0.1.11.post5-cp27-none-linux_x86_64.whl
pip install torchvision

# virtual display
dnf install -y xorg-x11-server-Xvfb
export DISPLAY=:99.0
Xvfb :99 -screen 0 1024x768x16 &> xvfb.log  &
sleep 3  # give xvfb some time to start

# unit tests
dnf install -y PyQt4
cd /guibot
sh run_tests.sh

exit 0
