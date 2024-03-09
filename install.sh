#!/bin/bash

INSTALLER=$(realpath "$0")
HARTLEY=$(dirname "$INSTALLER")/hartley
chmod +x $HARTLEY

HARTLEY_TARGET_DIR=$HOME/.local/bin
mkdir -p $HARTLEY_TARGET_DIR && \
ln -sf $HARTLEY $HARTLEY_TARGET_DIR && \
{
  echo "Hartley installed successfully at $HARTLEY_TARGET_DIR/hartley. You can now run it by typing hartley in your terminal."
  echo "If the command is not found, you may need to add $HARTLEY_TARGET_DIR to your PATH environment variable."
}