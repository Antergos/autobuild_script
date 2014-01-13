#!/bin/bash

source /etc/auta/auta.config

_build_log(){
        echo "New Antergos Automatic Build ${arch} - $(date +%Y.%m.%d)" > /tmp/build_finished_${arch}.log
        echo >> /tmp/build_finished_${arch}.log
        echo "Build State: ${BUILD}" >> /tmp/build_finished_${arch}.log
        echo >> /tmp/build_finished_${arch}.log
        echo "Error Log:" >> /tmp/build_finished_${arch}.log
        echo >> /tmp/build_finished_${arch}.log
        cat /tmp/build_finished_${arch}.log /tmp/antergos_buildError_${arch}.log > /tmp/build_finished2_${arch}.log
        echo >> /tmp/build_finished2_${arch}.log
        echo "Build Log:" >> /tmp/build_finished2_${arch}.log
        echo >> /tmp/build_finished2_${arch}.log
        cat /tmp/build_finished2_${arch}.log /tmp/antergos_build_${arch}.log > /tmp/build_${arch}.log
}


# Build ISO
cd ${DIR}
./build.sh -v build > /tmp/antergos_build_${arch}.log 2> /tmp/antergos_buildError_${arch}.log
_build_log
