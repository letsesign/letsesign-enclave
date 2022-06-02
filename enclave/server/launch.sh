#!/bin/sh
set -e

# install rpm packages
rpm_package_list=""
readarray rpm_packages < /configs/enclave-rpm-packages.txt
for package in "${rpm_packages[@]}";do
  package=$(tr -d ' ' <<< "$package")
  rpm_package_list="${rpm_package_list} /packages/rpm/${package}.rpm"
done
rpm -ivh ${rpm_package_list}

# install python modules
pip3 install --no-index --find-links /packages/whl -r /server/requirements.txt

# install aws-nitro-enclaves-nsm-api
cp /packages/so/libnsm.so /usr/lib64/libnsm.so

# Assign an IP address to local loopback
ifconfig lo 127.0.0.1

# Add hosts record, pointing API endpoint to local loopback
readarray host_settings < /configs/enclave.hosts
for setting in "${host_settings[@]}";do                                                      
  echo "${setting}" >> /etc/hosts
done

# Run traffic forwarder in background
mkdir /var/log/traffic_forwarder
readarray traffic_forwarder_arguments < /configs/proxy.conf
for arguments in "${traffic_forwarder_arguments[@]}";do 
  argument_list=(${arguments})
  local_ip=${argument_list[0]}
  local_port=${argument_list[1]}
  remote_cid=${argument_list[2]}
  remote_port=${argument_list[3]}

  nohup python3 /server/traffic_forwarder.py ${local_ip} ${local_port} ${remote_cid} ${remote_port} > /var/log/traffic_forwarder/${remote_port}.log 2>&1 &
done

# unpack email template
(cd /server/resources/template && for z in *.gz; do tar xvf $z; done)

# start the main program
total_cpu=$(lscpu | grep  "^CPU(s):" | awk '{print $2}')
for i in $(seq $total_cpu);do 
  python3 /server/tee_server.py &
done

while true
do
	sleep 60
done