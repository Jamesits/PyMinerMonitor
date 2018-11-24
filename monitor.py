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

try:
    with open("config.json", "r") as config_file:
        config = json.load(config_file)
except:
    config = {
            "api": {},
            }

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
                sys.stdout.flush()
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
                # print("Failed to read data from device {}".format(name), file=sys.stderr)
                pass
            except json.decoder.JSONDecodeError:
                # print("Unexcepted data from device {}".format(name), file=sys.stderr)
                pass
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
                    ret_global = requests.get("{}/poolStats".format(config["url"]), timeout=5).json()
                    data = {
                        "difficulty": str(ret_global["network"]["difficulty"]) + "i",
                        "height": str(ret_global["network"]["height"]) + "i",
                        "reward": str(ret_global["network"]["reward"]) + "i",
                    }
                    print(InfluxDBLineProtocol("miner-pool-api-global", tags, data, int(ret_global["network"]["timestamp"]) * 1000000000))
                    sys.stdout.flush()
                except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
                    # print("Failed to read data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
                    pass
                except json.decoder.JSONDecodeError:
                    #print("Unexcepted data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
                    pass
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
                        sys.stdout.flush()
                except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
                    # print("Failed to read data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
                    pass
                except json.decoder.JSONDecodeError:
                    # print("Unexcepted data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
                    pass
                # worker stats
                try:
                    #time.sleep(10) # do not request too fast
                    ret_workers = requests.get("{}/stats/workerStats/{}".format(config["url"], address), timeout=5).json()
                    for worker in ret_workers["workers"]:
                        tags["rig_id"] = worker["rigId"]
                        data = {
                            "hashrate": disunitify(worker["hashRate"]),
                        }
                        print(InfluxDBLineProtocol("miner-pool-api-per-rig", tags, data))   
                        sys.stdout.flush()
                except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
                    # print("Failed to read data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
                    pass
                except json.decoder.JSONDecodeError:
                    # print("Unexcepted data from pool {} address {}".format(poolname, addr_alias), file=sys.stderr)
                    pass
    else:
        print("Unknown API type {}".format(k), file=sys.stderr)

measurement = "coin_price"
try:
    data = requests.get("https://api.coinmarketcap.com/v1/ticker/", params={"convert": "CNY"}).json()
    for coin in data:
        print(InfluxDBLineProtocol(measurement=measurement,
                                   tags={
                                       "id": coin["id"],
                                       "name": coin["name"].replace(" ", "\\ "),
                                       "symbol": coin["symbol"]
                                       },
                                   data={
                                        "rank": coin["rank"] + "i", 
                                        "price_usd": coin["price_usd"], 
                                        "price_btc": coin["price_btc"], 
                                        "24h_volume_usd": coin["24h_volume_usd"], 
                                        "market_cap_usd": coin["market_cap_usd"], 
                                        "available_supply": coin["available_supply"], 
                                        "total_supply": coin["total_supply"], 
                                        "max_supply": coin["max_supply"] or 0, 
                                        "percent_change_1h": coin["percent_change_1h"], 
                                        "percent_change_24h": coin["percent_change_24h"], 
                                        "percent_change_7d": coin["percent_change_7d"], 
                                        "price_cny": coin["price_cny"], 
                                        "24h_volume_cny": coin["24h_volume_cny"], 
                                        "market_cap_cny": coin["market_cap_cny"],
                                       },
                                   timestamp=int(coin["last_updated"]) * 1000000000,
                                   )
              )
        sys.stdout.flush()
except:
    pass
    

measurement = "smzdw"

for api in (
    "https://www.smzdw.org/json/gpu_mining.json",
    "https://www.smzdw.org/json/asic_mining.json",
):
    try:
        data = requests.get(api).json()
        for name, coin in data["coins"].items():
            print(InfluxDBLineProtocol(measurement=measurement,
                                       tags={
                                           "id": coin["id"],
                                           "name": name.replace(" ", "\\ "),
                                           "symbol": coin["tag"],
                                           "algorithm": coin["algorithm"].replace(" ", "\\ "),
                                           "exchange_rate_curr": coin["exchange_rate_curr"],
                                           },
                                       data={
                                            "block_time": coin["block_time"], 
                                            "block_reward": coin["block_reward"], 
                                            "block_reward24": coin["block_reward24"], 
                                            "last_block": str(coin["last_block"]) + "i", 
                                            "difficulty": coin["difficulty"], 
                                            "difficulty24": coin["difficulty24"],
                                            "nethash": coin["nethash"], 
                                            "exchange_rate": coin["exchange_rate"], 
                                            "exchange_rate24": coin["exchange_rate24"], 
                                            "exchange_rate_vol": coin["exchange_rate_vol"], 
                                            "market_cap": coin["market_cap"][1:].replace(",", ""), 
                                            "estimated_rewards": coin["estimated_rewards"], 
                                            "estimated_rewards24": coin["estimated_rewards24"], 
                                            "btc_revenue": coin["btc_revenue"], 
                                            "btc_revenue24": coin["btc_revenue24"],
                                            "profitability": str(coin["profitability"]) + "i",
                                            "profitability24": str(coin["profitability24"]) + "i",
                                           },
                                       timestamp=int(coin["timestamp"]) * 1000000000,
                                       )
                  )
            sys.stdout.flush()
    except:
        pass
