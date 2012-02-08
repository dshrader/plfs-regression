#!/bin/bash
#
# This script echos the first panfs scratch mount point located on the system
#
scratch_mount="`mount -t panfs | awk '{print $3}' | sed 's/\// /g' | awk '{print $2}' | head -1`"

if [ "$scratch_mount" == "" ]; then 
   echo "Error:  Unable to find panfs scratch space."
   scratch_mount="None"
else 
   if [ ! -e $scratch_mount/$USER ]; then
       scratch_mount="`find /panfs -maxdepth 3 -name atorrez | head -1`"
   fi
fi

echo $scratch_mount
