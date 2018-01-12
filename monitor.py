#!/usr/bin/env python3

import json
import sys
import requests
from typing import *
import time
import os

os.chdir(os.path.dirname(sys.argv[0]))

config = None

class InfluxDBLineProtocol:
    def __init__(self, measurement: str, tags: Dict[str, str], data: Dict[str, str], timestamp: int = int(time.time() * 1000000000)):
        self.measurement = measurement
        self.tags = tags or dict()
        self.data = data or dict()
        self.timestamp = timestamp

    def __str__(self):
        return "{},{} {} {}".format(self.measurement, ",".join("{}={}".format(k ,v) for k, v in self.tags.items()), ",".join("{}={}".format(k ,v) for k, v in self.data.items()), self.timestamp)

with open("config.json", "r") as config_file:
    config = json.load(config_file)

if not config:
    print("Cannot read config", file=sys.stderr)
    sys.exit(1)

for k, v in config["api"].items():
    if k == "xmr-stak":
        for name, config in v.items():
            try:
                ret = requests.get(config["url"], timeout=1).json()
                tags = {
                    "name": name
                }
                if "tags" in config:
                    tags = {**tags, **config["tags"]}
                data = {
                    "total_hashrate": ret["hashrate"]["total"][0],
                    "diff_current": ret["results"]["diff_current"],
                    "shares_good": ret["results"]["shares_good"],
                    "shares_total": ret["results"]["shares_total"],
                    "avg_time": ret["results"]["avg_time"],
                    "hashes_total": ret["results"]["hashes_total"],
                    "uptime": ret["connection"]["uptime"],
                    "ping": ret["connection"]["ping"],
                }
                print(InfluxDBLineProtocol("miner-xmr-stak", tags, data))
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout):
                print("Failed to read data from device {}".format(name), file=sys.stderr)
            except json.decoder.JSONDecodeError:
                print("Unexcepted data from device {}".format(name), file=sys.stderr)
    elif k == "pool-api":
        for poolname, config in v.items():
            for addr_alias, address in config["addresses"].items():
                tags = {
                    "pool": poolname,
                    "alias": addr_alias,
                    "address": address,
                }
                if "tags" in config:
                    tags = {**tags, **config["tags"]}
                # total stats
                try:
                    time.sleep(5) # do not request too fast
                    ret_total = requests.get("{}/stats/address/{}".format(config["url"], address), timeout=5).json()
                    for point in ret_total["charts"]["hashrate"]:
                        data = {
                            "hashrate": point[1],
                        }
                        print(InfluxDBLineProtocol("miner-xmr-stak", tags, data, point[0] * 1000000000))
                except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout):
                    print("Failed to read data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
                except json.decoder.JSONDecodeError:
                    print("Unexcepted data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
                # worker stats
                try:
                    time.sleep(5) # do not request too fast
                    ret_workers = requests.get("{}/stats/workerStats/{}".format(config["url"], address), timeout=5).json()
                    for worker in ret_workers["workers"]:
                        tags["rig_id"] = worker["rigId"]
                        data = {
                            "hashrate": worker["hashRate"],
                        }
                        print(InfluxDBLineProtocol("miner-xmr-stak", tags, data))   
                except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout):
                    print("Failed to read data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
                except json.decoder.JSONDecodeError:
                    print("Unexcepted data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
    else:
        print("Unknown API type {}".format(k), file=sys.stderr)
