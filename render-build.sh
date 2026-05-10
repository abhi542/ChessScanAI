#!/usr/bin/env bash
# exit on error
set -o errexit

# Install python dependencies
pip install -r requirements.txt

# Download Stockfish binary if it doesn't exist
if [ ! -f "stockfish_bin" ]; then
    echo "Downloading Stockfish 16.1..."
    wget -qO stockfish.tar https://github.com/official-stockfish/Stockfish/releases/download/sf_16.1/stockfish-ubuntu-x86-64-avx2.tar
    tar -xf stockfish.tar
    
    # Let's find the exact executable and move it to the root directory
    find . -type f -name "stockfish-ubuntu-x86-64-avx2" -exec mv {} ./stockfish_bin \;
    
    # Clean up the extracted folder and tar file
    rm stockfish.tar
    rm -rf stockfish/
    
    chmod +x stockfish_bin
    echo "Stockfish downloaded and installed."
else
    echo "Stockfish already installed."
fi
