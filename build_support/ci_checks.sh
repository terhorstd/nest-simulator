#!/bin/bash

# ci_build.sh
#
# This file is part of NEST.
#
# Copyright (C) 2004 The NEST Initiative
#
# NEST is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# NEST is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NEST.  If not, see <http://www.gnu.org/licenses/>.


# This shell script is part of the NEST CI build and test environment.
# It is invoked by the top-level Github Actions script '.github/workflows/nestbuildmatrix.yml'.
#
# NOTE: This shell script is tightly coupled to 'build_support/parse_build_log.py'.
#       Any changes to message numbers (MSGBLDnnnn) or the variable name
#      'file_names' have effects on the build/test-log parsing process.


# Exit shell if any subcommand or pipline returns a non-zero status.
set -euo pipefail


NEST_VPATH=build
mkdir -p "$NEST_VPATH/reports"

echo "+ + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + +"
echo "+               S T A T I C   C O D E   A N A L Y S I S                       +"
echo "+ + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + +"

echo "MSGBLD0010: Initializing VERA++ static code analysis."
export PYTHON_EXECUTABLE="$(which python3)"
export PYTHON_INCLUDE_DIR="$(python3 -c "import sysconfig; print(sysconfig.get_path('include'))")"
export PYLIB_BASE="lib$(basename $PYTHON_INCLUDE_DIR)"
export PYLIB_DIR="$(dirname $PYTHON_INCLUDE_DIR | sed 's/include/lib/')"
export PYTHON_LIBRARY="$(find $PYLIB_DIR \( -name $PYLIB_BASE.so -o -name $PYLIB_BASE.dylib \) -print -quit)"
echo "--> Detected PYTHON_LIBRARY=$PYTHON_LIBRARY"
echo "--> Detected PYTHON_INCLUDE_DIR=$PYTHON_INCLUDE_DIR"
CONFIGURE_PYTHON="-DPYTHON_EXECUTABLE=$PYTHON_EXECUTABLE -DPYTHON_LIBRARY=$PYTHON_LIBRARY -DPYTHON_INCLUDE_DIR=$PYTHON_INCLUDE_DIR"

# Add the NEST profile to the VERA++ profiles.
sudo cp build_support/vera++.profile /usr/lib/vera++/profiles/nest
echo "MSGBLD0020: VERA++ initialization completed."
if [ ! -f "$HOME/.cache/bin/cppcheck" ]; then
    echo "MSGBLD0030: Installing CPPCHECK version 1.69."
    # Build cppcheck version 1.69
    git clone https://github.com/danmar/cppcheck.git
    cd cppcheck
    git checkout tags/1.69
    mkdir -p install
    make PREFIX=$HOME/.cache CFGDIR=$HOME/.cache/cfg HAVE_RULES=yes install
    cd -
    echo "MSGBLD0040: CPPCHECK installation completed."

    echo "MSGBLD0050: Installing CLANG-FORMAT."
    wget --no-verbose http://llvm.org/releases/3.6.2/clang+llvm-3.6.2-x86_64-linux-gnu-ubuntu-14.04.tar.xz
    tar xf clang+llvm-3.6.2-x86_64-linux-gnu-ubuntu-14.04.tar.xz
    # Copy and not move because '.cache' may aleady contain other subdirectories and files.
    cp -R clang+llvm-3.6.2-x86_64-linux-gnu-ubuntu-14.04/* $HOME/.cache
    echo "MSGBLD0060: CLANG-FORMAT installation completed."

    # Remove these directories, otherwise the copyright-header check will complain.
    rm -rf cppcheck clang+llvm-3.6.2-x86_64-linux-gnu-ubuntu-14.04
fi

# Ensure that the cppcheck and clang-format installation can be found.
export PATH=$HOME/.cache/bin:$PATH

echo "MSGBLD0070: Retrieving changed files."
file_names=$CHANGED_FILES
echo "MSGBLD0071: $file_names"

# Note: uncomment the following line to static check *all* files, not just those that have changed.
# Warning: will run for a very long time

# file_names=$(find . -name "*.h" -o -name "*.c" -o -name "*.cc" -o -name "*.hpp" -o -name "*.cpp" -o -name "*.py")

for single_file_name in $file_names
do
    echo "MSGBLD0095: File changed: $single_file_name"
done
echo "MSGBLD0100: Retrieving changed files completed."
echo

# Set the command line arguments for the static code analysis script and execute it.

# The names of the static code analysis tools executables.
VERA=vera++
CPPCHECK=cppcheck
CLANG_FORMAT=clang-format
PEP8=pycodestyle
PYCODESTYLE_IGNORES="E121,E123,E126,E226,E24,E704,W503,W504"

# Perform or skip a certain analysis.
PERFORM_VERA=true
PERFORM_CPPCHECK=true
PERFORM_CLANG_FORMAT=true
PERFORM_PEP8=true

# The following command line parameters indicate whether static code analysis error messages
# will cause the CI build to fail or are ignored.
IGNORE_MSG_VERA=false
IGNORE_MSG_CPPCHECK=true
IGNORE_MSG_CLANG_FORMAT=false
IGNORE_MSG_PYCODESTYLE=false

# The script is called within the CI environment and thus can not be run incremental.
RUNS_ON_CI=true
INCREMENTAL=false

./build_support/static_code_analysis.sh "$RUNS_ON_CI" "$INCREMENTAL" "$file_names" "$NEST_VPATH" \
"$VERA" "$CPPCHECK" "$CLANG_FORMAT" "$PEP8" \
"$PERFORM_VERA" "$PERFORM_CPPCHECK" "$PERFORM_CLANG_FORMAT" "$PERFORM_PEP8" \
"$IGNORE_MSG_VERA" "$IGNORE_MSG_CPPCHECK" "$IGNORE_MSG_CLANG_FORMAT" "$IGNORE_MSG_PYCODESTYLE" \
"$PYCODESTYLE_IGNORES"

exit $?
