### Autobuild Script to create testing Antergos images

The script will be executed every Sunday at 6:00am (UTC/GMT +1). The final image will have 
latest git code from our account (master branch).

An email is sent to the private mailing list of Antergos dev team with state of building and some other information.

These images, will be available from http://mirrors.antergos.com/iso/testing. In the same folder, a build.log will be
available with buildings logs, separated stdout from stderr.

Place antergos_autobuild.config in /etc
Place autobuild_antergos.sh and build_execute.sh in /usr/bin
Run /usr/bin/autobuild_antergos.sh