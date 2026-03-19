#!/bin/sh

set -e

# Update package lists and install Python 3 and pip
sudo apt update
sudo apt install -y python3 python3-pip

# Install j2735_202409 package
git clone https://github.com/usdot-fhwa-stol/j2735_202409.git
cd j2735_202409
python3 -m pip install --break-system-packages dist/j2735_202409-0.1.0-py3-none-any.whl
cd ..
rm -rf j2735_202409
