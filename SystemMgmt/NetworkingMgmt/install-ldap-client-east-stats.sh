#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

#Let's stop SSH first to avoid confusing people who try to connect straight away.
#It may be useful to comment this out for debuging & connecting whilst the script is running
service ssh stop

apt-get update

apt-get -y install curl resolvconf libpam-ldapd libpam-cracklib nscd patch

#This is so that the system can find the LDAP servers even in the dark
echo "10.92.1.11 dc1.aws-us-e1-bur.blinkx" >> /etc/hosts
echo "10.92.11.11 dc2.aws-us-e1-bur.blinkx" >> /etc/hosts
echo "10.92.21.11 dc3.aws-us-e1-bur.blinkx" >> /etc/hosts

#Creating the LDAP client configuration file from the example file
gunzip /usr/share/doc/nslcd/examples/nslcd.conf.gz
cat << 'EOF' | patch /usr/share/doc/nslcd/examples/nslcd.conf -o /etc/nslcd.conf
--- /usr/share/doc/nslcd/examples/nslcd.conf	2011-08-03 19:55:12.000000000 +0000
+++ /etc/nslcd.conf	2014-12-04 20:33:04.736387962 +0000
@@ -15,14 +15,14 @@
 #uri ldaps://127.0.0.1/
 #uri ldapi://%2fvar%2frun%2fldapi_sock/
 # Note: %2f encodes the '/' used as directory separator
-uri ldap://127.0.0.1/
+uri ldap://dc1.aws-us-e1-bur.blinkx/ ldap://dc2.aws-us-e1-bur.blinkx/ ldap://dc3.aws-us-e1-bur.blinkx/
 
 # The LDAP version to use (defaults to 3
 # if supported by client library)
-#ldap_version 3
+ldap_version 3
 
 # The distinguished name of the search base.
-base dc=example,dc=com
+base dc=blinkx,dc=com
 
 # The distinguished name to bind to the server with.
 # Optional: default is to bind anonymously.
@@ -34,19 +34,18 @@
 #bindpw secret
 
 # The distinguished name to perform password modifications by root by.
-#rootpwmoddn cn=admin,dc=example,dc=com
+rootpwmoddn cn=admin,dc=blinkx,dc=com
 
 # The default search scope.
-#scope sub
-#scope one
-#scope base
+scope sub
 
 # Customize certain database lookups.
-#base   group  ou=Groups,dc=example,dc=com
-#base   passwd ou=People,dc=example,dc=com
-#base   shadow ou=People,dc=example,dc=com
-#scope  group  onelevel
-#scope  hosts  sub
+base	passwd         ou=People,dc=blinkx,dc=com
+base	passwd         ou=Services,dc=blinkx,dc=com
+base	shadow         ou=People,dc=blinkx,dc=com
+base	shadow         ou=Services,dc=blinkx,dc=com
+base	group          ou=common,ou=Groups,dc=blinkx,dc=com
+base	group          ou=BUR,ou=Groups,dc=blinkx,dc=com
 
 # Bind/connect timelimit.
 #bind_timelimit 30
@@ -59,12 +58,12 @@
 #idle_timelimit 3600
 
 # Use StartTLS without verifying the server certificate.
-#ssl start_tls
-#tls_reqcert never
+ssl start_tls
+tls_reqcert hard
 
 # CA certificates for server certificate verification
 #tls_cacertdir /etc/ssl/certs
-#tls_cacertfile /etc/ssl/ca.cert
+tls_cacertfile /usr/share/ca-certificates/blinkx/Blinkx_Root.crt
 
 # Seed the PRNG if /dev/urandom is not provided
 #tls_randfile /var/run/egd-pool
EOF

#Randomize the servers order
/bin/sed -i "s#^uri.*\$#$(echo uri $(for i in $(seq 1 3 |sort -R); do echo -n " ldap://dc$i.aws-us-e1-bur.blinkx/"; done))#g" /etc/nslcd.conf

#Polish PAM config"
echo "session required        pam_mkhomedir.so skel=/etc/skel/ umask=0022" >> /etc/pam.d/common-session
sed -i "s/compat/compat ldap/g" /etc/nsswitch.conf
sed -i 's/minimum_uid=1000/minimum_uid=5000/' /etc/pam.d/common-*
pam-auth-update

#Install basic sudo rules
echo "%super_admin ALL=(ALL) ALL" >> /etc/sudoers.d/blinkx
echo "%BUR_admin ALL=(ALL) ALL" >> /etc/sudoers.d/blinkx
chmod u-w,o= /etc/sudoers.d/blinkx

#Support domain searching in the AZ (requires the resolvconf package to be installed)
echo "  dns-search $(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone | grep -o .$).aws-us-e1-bur.blinkx" >> /etc/network/interfaces

#Configure sshd
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config
sed -i 's/PermitRootLogin yes/PermitRootLogin no/g' /etc/ssh/sshd_config
/bin/echo -e "\nDenyGroups nologin" >> /etc/ssh/sshd_config

#Randomize LDAP servers order at startup
cat << 'EOF' >> /etc/crontab
@reboot root /bin/sed -i "s#^uri.*\$#$(echo uri $(for i in $(seq 1 3 |sort -R); do echo -n " ldap://dc$i.aws-us-e1-bur.blinkx/"; done))#g" /etc/ldap.conf && /usr/sbin/service libnss-ldap restart
EOF

#Reload necessary components
service ssh start
service cron restart
service nslcd restart
service networking reload
