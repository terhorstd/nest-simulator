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

env

NEST_VPATH=build
mkdir -p "$NEST_VPATH/reports"

echo
echo "+ + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + +"
echo "+               C O N F I G U R E   N E S T   B U I L D                       +"
echo "+ + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + +"

echo "MSGBLD0232: Setting configuration variables."

# Set the NEST CMake-build configuration according to the variables
# set above based on the ones set in the build stage matrix in
# '.github/workflows/nestbuildmatrix.yml'.

CONFIGURE_OPENMP="-Dwith-openmp=${WITH_OPENMP:-OFF}"
CONFIGURE_MPI="-Dwith-mpi=${WITH_MPI:-OFF}"

if [ "$WITH_PYTHON" = "ON" ] ; then
    export PYTHON_INCLUDE_DIR="$(python3 -c "import sysconfig; print(sysconfig.get_path('include'))")"
    export PYLIB_BASE="lib$(basename $PYTHON_INCLUDE_DIR)"
    export PYLIB_DIR="$(dirname $PYTHON_INCLUDE_DIR | sed 's/include/lib/')"
    export PYTHON_LIBRARY="$(find $PYLIB_DIR \( -name $PYLIB_BASE.so -o -name $PYLIB_BASE.dylib \) -print -quit)"
    echo "--> Detected PYTHON_LIBRARY=$PYTHON_LIBRARY"
    echo "--> Detected PYTHON_INCLUDE_DIR=$PYTHON_INCLUDE_DIR"
    CONFIGURE_PYTHON="-DPYTHON_LIBRARY=$PYTHON_LIBRARY -DPYTHON_INCLUDE_DIR=$PYTHON_INCLUDE_DIR"
    mkdir -p $HOME/.matplotlib
    echo "backend : svg" > $HOME/.matplotlib/matplotlibrc
else
    CONFIGURE_PYTHON="-Dwith-python=${WITH_PYTHON:-OFF}"
fi

if [ "$WITH_MUSIC" = "ON" ] ; then
    CONFIGURE_MUSIC="-Dwith-music=$HOME/.cache/music.install"
    ./build_support/install_music.sh
else
    CONFIGURE_MUSIC="-Dwith-music=${WITH_MUSIC:-OFF}"
fi

CONFIGURE_GSL="-Dwith-gsl=${WITH_GSL:-OFF}"
CONFIGURE_LTDL="-Dwith-ltdl=${WITH_LTDL:-OFF}"
CONFIGURE_READLINE="-Dwith-readline=${WITH_READLINE:-OFF}"

if [ "$WITH_LIBBOOST" = "ON" ] ; then
    #CONFIGURE_BOOST="-Dwith-boost=$HOME/.cache/boost_1_72_0.install"
    CONFIGURE_BOOST="-Dwith-boost=$HOME/.cache/boost_1_71_0.install"
    ./build_support/install_libboost.sh
else
    CONFIGURE_BOOST="-Dwith-boost=${WITH_LIBBOOST:-OFF}"
fi
if [ "$WITH_SIONLIB" = "1" ] ; then
    CONFIGURE_SIONLIB="-Dwith-sionlib=$HOME/.cache/sionlib.install"
    ./build_support/install_sionlib.sh
else
    CONFIGURE_SIONLIB="-Dwith-sionlib=${WITH_SIONLIB:-OFF}"
fi
if [ "$WITH_LIBNEUROSIM" = "ON" ] ; then
    CONFIGURE_LIBNEUROSIM="-Dwith-libneurosim=$HOME/.cache/libneurosim.install"
    ./build_support/install_csa-libneurosim.sh $PYLIB_DIR
    PYMAJOR="$(python3 -c 'import sys; print("%i.%i" % sys.version_info[:2])')"
    export PYTHONPATH=$HOME/.cache/csa.install/lib/python$PYMAJOR/site-packages${PYTHONPATH:+:$PYTHONPATH}
    if [[ $OSTYPE == darwin* ]]; then
        export DYLD_LIBRARY_PATH=$HOME/.cache/csa.install/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}
    else
        export LD_LIBRARY_PATH=$HOME/.cache/csa.install/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
    fi
else
    CONFIGURE_LIBNEUROSIM="-Dwith-libneurosim=${WITH_LIBNEUROSIM:-OFF}"
fi


cp examples/sli/nestrc.sli ~/.nestrc
# Explicitly allow MPI oversubscription. This is required by Open MPI versions > 3.0.
# Not having this in place leads to a "not enough slots available" error.
#if [[ "$OSTYPE" = darwin* ]] ; then
    #sed -i -e 's/mpirun -np/mpirun --oversubscribe -np/g' ~/.nestrc
#fi
sed -i -e 's/mpirun -np/mpirun --oversubscribe -np/g' ~/.nestrc
NEST_RESULT=result
if [ "$(uname -s)" = 'Linux' ]; then
    NEST_RESULT=$(readlink -f $NEST_RESULT)
else
    NEST_RESULT=$(greadlink -f $NEST_RESULT)
fi
mkdir "$NEST_RESULT"
echo "MSGBLD0235: Running CMake."
cd "$NEST_VPATH"
CMAKE_LINE="cmake \
    -DCMAKE_INSTALL_PREFIX="$NEST_RESULT" \
    -DCMAKE_CXX_FLAGS="$CXX_FLAGS" \
    -Dwith-optimize=ON \
    -Dwith-warning=ON \
    $CONFIGURE_BOOST \
    $CONFIGURE_OPENMP \
    $CONFIGURE_MPI \
    $CONFIGURE_PYTHON \
    $CONFIGURE_MUSIC \
    $CONFIGURE_GSL \
    $CONFIGURE_LTDL \
    $CONFIGURE_READLINE \
    $CONFIGURE_SIONLIB \
    $CONFIGURE_LIBNEUROSIM \
    .."
echo "MSGBLD0236: $(pwd)\$ $CMAKE_LINE"
$CMAKE_LINE                          # <---- RUN CMAKE IS HERE

echo "MSGBLD0240: CMake configure completed."
echo
echo "+ + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + +"
echo "+               B U I L D   N E S T                                           +"
echo "+ + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + +"
echo "MSGBLD0250: Running Make."
make VERBOSE=1
echo "MSGBLD0260: Make completed."
echo
echo "+ + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + +"
echo "+               I N S T A L L   N E S T                                       +"
echo "+ + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + +"
echo "MSGBLD0270: Running make install."
make install
echo "MSGBLD0280: Make install completed."
echo
echo "+ + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + +"
echo "+               R U N   N E S T   T E S T S U I T E                           +"
echo "+ + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + +"
echo "MSGBLD0290: Running make installcheck."
make installcheck
echo "MSGBLD0300: Make installcheck completed."
echo "MSGBLD0340: Build completed."
