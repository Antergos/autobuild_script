#!/bin/bash

DIR="/home/antergos"
CODE_DIR="/tmp/code_build_antergos"
CNCHI_INSTALL="/home/antergos/root-image/"
URL="http://mirrors.antergos.com/iso/testing"

iso_name=antergos
iso_version=$(date +%Y.%m.%d)
arch=$(uname -m)

# Mail config
TO="antergos-dev@mailman.antergos.com"
FROM="info@antergos.com"

_clean_build(){
        rm -rf ${DIR}/{work,out}
        rm -rf ${CNCHI_INSTALL}/usr/bin/cnchi
        rm -rf ${CNCHI_INSTALL}/usr/share/cnchi/

        for files in po/*; do
                if [ -f "$files" ] && [ "$files" != 'po/cnchi.pot' ]; then
                STRING_PO=`echo ${files#*/}`
                STRING=`echo ${STRING_PO%.po}`
                rm -rf ${CNCHI_INSTALL}/usr/share/locale/${STRING}/LC_MESSAGES/cnchi.mo
                fi
        done
}

_get_code(){
        mkdir -p ${CODE_DIR}
        cd ${CODE_DIR}
        git clone https://github.com/Antergos/Cnchi
}

_install_cnchi(){
        cd ${CODE_DIR}/Cnchi
        install -d ${CNCHI_INSTALL}/usr/share/cnchi
        install -Dm755 "cnchi.py" "${CNCHI_INSTALL}/usr/share/cnchi/cnchi.py"
        install -Dm755 "cnchi" "${CNCHI_INSTALL}/usr/bin/cnchi"

        for i in data scripts src ui; do
                cp -R ${i} "${CNCHI_INSTALL}/usr/share/cnchi/"
        done

        for files in po/*; do
                if [ -f "$files" ] && [ "$files" != 'po/cnchi.pot' ]; then
                STRING_PO=`echo ${files#*/}`
                STRING=`echo ${STRING_PO%.po}`
                mkdir -p ${CNCHI_INSTALL}/usr/share/locale/${STRING}/LC_MESSAGES
                msgfmt $files -o ${CNCHI_INSTALL}/usr/share/locale/${STRING}/LC_MESSAGES/cnchi.mo
                fi
        done
}

_build_log(){
        echo "New Antergos Automatic Build - $(date +%Y.%m.%d)" > /tmp/build_finished.log
        echo >> /tmp/build_finished.log
        echo "Build State: ${BUILD}" >> /tmp/build_finished.log
        echo >> /tmp/build_finished.log
        echo "Error Log:" >> /tmp/build_finished.log
        echo >> /tmp/build_finished.log
        cat /tmp/build_finished.log /tmp/antergos_buildError.log > /tmp/build_finished2.log
        echo >> /tmp/build_finished2.log
        echo "Build Log:" >> /tmp/build_finished2.log
        echo >> /tmp/build_finished2.log
        cat /tmp/build_finished2.log /tmp/antergos_build.log > /tmp/build_finished.log
}

_move_files(){
        rm -rf /var/www/antergos/iso/testing/*
        mv ${DIR}/out/* /var/www/antergos/iso/testing/
        mv /tmp/build_finished.log /var/www/antergos/iso/testing/build.log
}
_send_mail(){
        echo "New Antergos Automatic Build - $(date +%Y.%m.%d)" > /tmp/antergos_mail
        echo >> /tmp/antergos_mail
        echo "Build State: ${BUILD}" >> /tmp/antergos_mail
        echo "URL: ${URL}/${iso_name}-${iso_version}-${arch}.iso" >> /tmp/antergos_mail
        echo >> /tmp/antergos_mail
        echo "Log Output: ${URL}/build.log" >> /tmp/antergos_mail
        echo >> /tmp/antergos_mail


        mail -s "Antergos Automatic Build - $(date +%Y.%m.%d)" -aFrom:${FROM} ${TO} < /tmp/antergos_mail

        rm -rf /tmp/antergos*
        rm -rf /tmp/build*
}

# Clean directory to start new build
if [[ -e ${DIR}/work ]];then
        _clean_build
        if [[ -e ${CODE_DIR}/Cnchi ]];then
                rm -rf ${CODE_DIR}/Cnchi
        fi
fi

# Building GIT branch of Cnchi
_get_code
_install_cnchi

# Build ISO
cd ${DIR}
./build.sh -v build > /tmp/antergos_build.log 2> /tmp/antergos_buildError.log

if [[ -e ${DIR}/out ]];then
        BUILD="Success!"
else
        BUILD="Failed!"
fi

_build_log
_move_files
_send_mail