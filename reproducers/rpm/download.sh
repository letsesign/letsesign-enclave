#!/bin/sh

# download npm packages
rpm_package_list=""
readarray rpm_packages < enclave-rpm-packages.txt
for package in "${rpm_packages[@]}";do                                                      
  rpm_package_list="${rpm_package_list} ${package}"
done

yumdownloader --destdir /rpm ${rpm_package_list}
