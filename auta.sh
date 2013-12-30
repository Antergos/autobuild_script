#!/bin/bash

source /etc/auta/auta.config

_clean_build(){
        echo "> Cleaning the working environment..."
        rm -rf /tmp/{antergos*,build*}
        rm -rf ${DIR}
        echo ">< Cleaning the working environment * DONE *"
}

_move_files(){
        rm -rf /var/www/antergos/iso/testing/*
        echo "> Moving generated images to destination folder..."
        mv ${DIR}/out/* /var/www/antergos/iso/testing/
        echo ">< Moving generated images to destination folder * DONE *"
        echo "> Moving log files to destination folder..."
        mv /tmp/build_{i686,x86_64}.log /var/www/antergos/iso/testing/
        echo ">< Moving log files to destination folder * DONE *"
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
        echo ">< Cnchi finished..."
        git clone https://github.com/Antergos/antergos-iso
        echo ">< anteros-iso finished..."
}

_set_working_environment(){
        mkdir -p /home/antergos
        mv ${CODE_DIR}/antergos-iso/configs/antergos ${DIR}
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
if [[ -e ${CODE_DIR} ]];then
        rm -rf ${CODE_DIR}
fi

echo "> Downloading the code..."
_get_code
echo ">< Downloading the code * DONE *"


echo "> Creating /home/antergos as working environment..."
# Set working environment /home/antergos
_set_working_environment
echo ">< Creating /home/antergos as working environment * DONE *"

echo "> Installing latest Cnchi code..."
# Building GIT branch of Cnchi
_install_cnchi
echo ">< Installing latest Cnchi code * DONE *"


# Build x86_64 version
echo "> Generating x86_64 Image..."
auta-build.sh
echo ">< Generating x86_64 Image * DONE *"
#Build i686 version
echo "> Generating i686 Image..."
linux32 auta-build.sh
echo ">< Generating i686 Image * DONE *"


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
