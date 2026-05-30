#!/usr/bin/env bash
# Install Python dependencies
pip install -r requirements.txt

# Download and extract the Linux Stockfish binary
echo "Downloading Stockfish..."
wget https://github.com/official-stockfish/Stockfish/releases/download/sf_16.1/stockfish-ubuntu-x86-64-avx2.tar
tar -xvf stockfish-ubuntu-x86-64-avx2.tar
chmod +x stockfish/stockfish-ubuntu-x86-64-avx2
echo "Stockfish installed successfully!"
