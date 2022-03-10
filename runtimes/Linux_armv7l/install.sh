#!/bin/bash

dir=$(cd -P -- "$(dirname -- "$0")" && pwd -P)
cd $dir

sudo apt update && sudo apt install -y python3-pip python3-venv

mv runtime runtime_A

mkdir -p data
echo "A" > data/active_runtime

service_exists() {
    local n=$1
    if [[ $(systemctl list-units --all -t service --full --no-legend "$n.service" | sed 's/^\s*//g' | cut -f1 -d' ') == $n.service ]]; then
        return 0
    else
        return 1
    fi
}
if service_exists terrathings; then
    echo "Stopping terrathings service"
    sudo systemctl stop terrathings
fi

echo "Copy systemd file"
sudo cp systemd/terrathings.service /etc/systemd/system/

echo "Creating pip cache folder"
mkdir -p .cache/pip && sudo chown root:root .cache/pip

echo "Enable service"
sudo systemctl daemon-reload && sudo systemctl enable terrathings.service && sudo systemctl start terrathings.service
