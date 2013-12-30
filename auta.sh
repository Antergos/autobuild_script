#!/bin/bash

source /etc/auta/auta.config

_clean_build(){
        rm -rf /tmp/{antergos*,build*}
        rm -rf ${DIR}/{work,out}
        rm -rf ${CNCHI_INSTALL}/usr/bin/cnchi
        rm -rf ${CNCHI_INSTALL}/usr/share/locale/*/LC_MESSAGES/cnchi.*
}

_move_files(){
        rm -rf /var/www/antergos/iso/testing/*
        mv ${DIR}/out/* /var/www/antergos/iso/testing/
        mv /tmp/build_{i686,x86_64}.log /var/www/antergos/iso/testing/
}
_send_mail(){
        echo "New Antergos Automatic Build - $(date +%Y.%m.%d)" >> /tmp/antergos_mail
        echo >> /tmp/antergos_mail
        echo "Build State x86_64: ${BUILD_x86_64}" >> /tmp/antergos_mail
        echo "URL: ${URL}/${iso_name}-${iso_version}-x86_64.iso" >> /tmp/antergos_mail
        echo "Log Output: ${URL}/build_x86_64.log" >> /tmp/antergos_mail
        echo >> /tmp/antergos_mail
	echo "Build State i686: ${BUILD_i686}" >> /tmp/antergos_mail
	echo "URL: ${URL}/${iso_name}-${iso_version}-i686.iso" >> /tmp/antergos_mail
	echo "Log Output: ${URL}/build_i686.log" >> /tmp/antergos_mail
	echo >> /tmp/antergos_mail

        mail -s "Antergos Automatic Build - $(date +%Y.%m.%d)" -aFrom:${FROM} ${TO} < /tmp/antergos_mail
}

_get_code(){
        mkdir -p ${CODE_DIR}
        cd ${CODE_DIR}
        git clone -b testing https://github.com/Antergos/Cnchi
}


_install_cnchi(){
        cd ${CODE_DIR}/Cnchi
        install -d ${CNCHI_INSTALL}/usr/share/cnchi
        install -Dm755 "cnchi.py" "${CNCHI_INSTALL}/usr/share/cnchi/cnchi.py"
        install -Dm755 "cnchi" "${CNCHI_INSTALL}/usr/bin/cnchi"

        for i in data scripts src ui; do
                cp -Rf ${i} "${CNCHI_INSTALL}/usr/share/cnchi/"
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


# Clean directory to start new build
if [[ -e ${DIR}/work ]];then
        _clean_build
fi
if [[ -e ${CODE_DIR}/Cnchi ]];then
        rm -rf ${CODE_DIR}/Cnchi
fi

_get_code

# Building GIT branch of Cnchi
_install_cnchi


# Build x86_64 version
auta-build.sh
#Build i686 version
linux32 auta-build.sh


if [[ -e ${DIR}/out/${iso_name}-${iso_version}-x86_64.iso ]];then
        BUILD_x86_64="Success!"
	BUILD="1"
else
        BUILD_x86_64="Failed!"
fi

if [[ -e ${DIR}/out/${iso_name}-${iso_version}-i686.iso ]];then
        BUILD_i686="Success!"
	BUILD="1"
else
        BUILD_i686="Failed!"
fi


if [[ "${BUILD}" == "1" ]];then
	_move_files
fi
_send_mail
