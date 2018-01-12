# PyMinerMonitor

Collect hash rates from miner and log to InfluxDB automatically.

Supported data source:

 * xmr-stak
 * etn.spacepools.org API (probably compatible with other pools; I didn't test)

## Requirements

 * Python 3 and pip
 * Network connection
 * Telegraf (You probably need InfluxDB too)

## Installation

```shell
cd /usr/local/src
git clone https://github.com/Jamesits/PyMinerMonitor.git
cd PyMinerMonitor
sudo -H pip3 install -r requirements.txt
```

## Usage

Add the following code to `/etc/telegraf/telegraf.conf`:

```toml
# Read metrics from one or more commands that can output to stdout
[[inputs.exec]]
  ## Commands array
  commands = [
        "/usr/local/src/PyMinerMonitor/monitor.py"
  ] 

  ## Timeout for each command to complete.
  timeout = "120s"

  ## measurement name suffix (for separating different commands)
  name_suffix = ""

  ## Data format to consume.
  ## Each data format has its own unique set of configuration options, read
  ## more about them here:
  ## https://github.com/influxdata/telegraf/blob/master/docs/DATA_FORMATS_INPUT.md
  data_format = "influx"
```

## Notes

Donation to author:
 * BTC `1Cm42dB58VcHFC4HZSToMESGbXJr82JaSZ`
 * ETH `0x6fDEb40271b9E027CAF6Fb4feBF5432a9F36EF1F`