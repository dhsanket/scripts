#!/bin/bash
#
# global.sh | 2014-12-03 | jgreeman@blinkx.com
# adapted from the 12_04 global.sh
#
# DESCRIPTION:
# 
# Global user-data script for EC2 instance deployment. 
#
# Deploys:
#   * Ansible admin user & credentials
#   * DataDog agent software
#   * Mail relay settings & postmaster alias
#   * LDAP (although some of the security appliances may not be using LDAP, TBD)
#
# References:
#   * https://bitbucket.org/blinkxdev/aws-build-scripts/
#   * https://blinkx.atlassian.net/browse/VMTA-143

## REQUIRED (DO NOT MODIFY):
SCRIPTS="add-ansible-user add-root-keys install-ntp-client install-datadog install-ldap-client-east-video install-postfix "

for script in $SCRIPTS; do
	wget "http://repo-int.aws.blnx.us/cloud-init/aws-build-scripts/ubuntu-14-04/_all/$script.sh"
	chmod +x $script.sh
	./$script.sh
	rm $script.sh
done
