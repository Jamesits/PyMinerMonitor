#!/usr/bin/env python3

import json
import sys
import requests
from typing import *
import time
import os

os.chdir(os.path.dirname(sys.argv[0]))

config = None

def disunitify(s: str) -> float:
    num, unit = s.split()
    num = float(num)
    unit = unit.lower()
    if unit.startswith("k"):
        num *= 1000
    elif unit.startswith("m"):
        num *= 1000000
    
    return num

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
                ret = requests.get(config["url"], timeout=5).json()
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
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
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
                # global stats
                try:
                    ret_global = requests.get("{}/price".format(config["url"]), timeout=5).json()
                    data = {
                        "price_usd": ret_global[0]["price_usd"],
                        "price_btc": ret_global[0]["price_btc"],
                        "24h_volume_usd": ret_global[0]["24h_volume_usd"],
                        "market_cap_usd": ret_global[0]["market_cap_usd"],
                        "available_supply": ret_global[0]["available_supply"],
                        "percent_change_1h": ret_global[0]["percent_change_1h"],
                    }
                    print(InfluxDBLineProtocol("miner-pool-api-global", tags, data, int(ret_global[0]["last_updated"]) * 1000000000))
                except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
                    print("Failed to read data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
                except json.decoder.JSONDecodeError:
                    print("Unexcepted data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
                # total stats
                try:
                    ret_total = requests.get("{}/stats/address/{}".format(config["url"], address), timeout=5).json()
                    data = {
                        "total_hashes": ret_total["stats"]["hashes"],
                        "balance": float(ret_total["stats"]["balance"]) / 100,
                        "paid": float(ret_total["stats"]["paid"]) / 100,
                        "hashrate_10min_avg": disunitify(ret_total["stats"]["hashrate"]),
                    }
                    print(InfluxDBLineProtocol("miner-pool-api-account", tags, data, int(ret_total["stats"]["lastShare"]) * 1000000000))
                    for point in ret_total["charts"]["hashrate"]:
                        data = {
                            "hashrate": float(point[1]),
                        }
                        print(InfluxDBLineProtocol("miner-pool-api", tags, data, point[0] * 1000000000))
                except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
                    print("Failed to read data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
                except json.decoder.JSONDecodeError:
                    print("Unexcepted data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
                # worker stats
                try:
                    time.sleep(10) # do not request too fast
                    ret_workers = requests.get("{}/stats/workerStats/{}".format(config["url"], address), timeout=5).json()
                    for worker in ret_workers["workers"]:
                        tags["rig_id"] = worker["rigId"]
                        data = {
                            "hashrate": disunitify(worker["hashRate"]),
                        }
                        print(InfluxDBLineProtocol("miner-pool-api-per-rig", tags, data))   
                except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
                    print("Failed to read data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
                except json.decoder.JSONDecodeError:
                    print("Unexcepted data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
    else:
        print("Unknown API type {}".format(k), file=sys.stderr)
