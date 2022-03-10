#!/bin/bash

cmd=$(journalctl _SYSTEMD_INVOCATION_ID=`systemctl show -p InvocationID --value terrathings.service` | grep "Application startup complete.")

if [[ $cmd ]]; then
	echo true
else
	echo false
fi
