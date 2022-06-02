#!/bin/sh

# download python packages
python_package_list=""
readarray python_packages < requirements-lock.txt
for package in "${python_packages[@]}";do                                                      
  python_package_list="${python_package_list} ${package}"
done

pip3 download -d /whl ${python_package_list}
