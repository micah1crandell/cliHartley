#!/bin/bash

INSTALLER=$(realpath "$0")
SABINE=$(dirname "$INSTALLER")/sabine
chmod +x $SABINE

SABINE_TARGET_DIR=$HOME/.local/bin
mkdir -p $SABINE_TARGET_DIR && \
ln -sf $SABINE $SABINE_TARGET_DIR && \
{
  echo "SABINE installed successfully at $SABINE_TARGET_DIR/sabine. You can now run it by typing sabine in your terminal."
  echo "If the command is not found, you may need to add $SABINE_TARGET_DIR to your PATH environment variable."
}
