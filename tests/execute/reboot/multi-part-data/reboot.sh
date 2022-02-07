#!/bin/bash

if [ "$REBOOTCOUNT" -eq 1 ]; then
	echo "Rebooted"
else
	echo "Rebooting"
	tmt-reboot
fi
