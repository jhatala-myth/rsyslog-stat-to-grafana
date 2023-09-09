#!/usr/bin/env python3
import os
import sys
import re
import argparse
import json
import time
from datetime import datetime, timedelta
import pickle
import struct
import socket


# parsing maps
stat_block_map = r'(?:BEGIN)(?P<statistic>[\s\S]+?)(?:END)'
# rsyslog has a weird timestamp for impstat with cee format
# Tue Jul 18 09:20:06 2023: @cee: { "name": "test queue", "origin": "core.queue", "size": 0, "enqueued": 21395, "full": 0, "discarded.full": 0, "discarded.nf": 0, "maxqsize": 5602 }
stat_json_map = r'^(?P<timestamp>\w{3}\s\w{3}\s\d{2}\s(?:\d{2}:?){3}\s\d{4}):\s@cee:\s(?P<json>.+)$'
stat_timestamp = "%a %b %d %H:%M:%S %Y"

impstat_file = ""

def json_to_dot(node, path=None):
    path = path[:] if path else []
    if isinstance(node, list):
        for index, item in enumerate(node):
            yield from json_to_dot(item, path)
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from json_to_dot(value, path + [key])
    else:
        yield {','.join(path): node}

def json_stat_cleanup(in_json, to_delete):
    for item in to_delete:
        if item in in_json.keys():
            del in_json[item]
    return in_json

def reset_counters(json_stat):
    for key in json_stat.keys():
        json_stat[key] = 0

def main():
    # look for a config filefaz-cisco_as
    config = {}
    config_file = "{}/{}.conf".format(os.path.dirname(os.path.abspath(__file__)),
                                      os.path.splitext(os.path.basename(__file__))[0])

    if os.path.isfile(config_file):
        with open(config_file) as json_file:
            try:
                config = json.load(json_file)[0]
            except ValueError:
                print("Config load error")
                exit(1)

    # validate config
    if not os.path.exists(config["impstats_file"]):
        print("stat file doesn't exists")
        exit(1)

    cmd_parser = argparse.ArgumentParser(description="rSyslog impstats collector")
    cmd_parser.add_argument("-zabbix", required=False, choices=["yes", "no"], help="Output for zabbix agent")

    config.update(vars(cmd_parser.parse_args()))

    # define variables
    tuples = []
    stat_string = ''
    update_time = int(time.time())
    origin = socket.gethostname().replace(".", "-") + config["metric_tag"]

    # read file from end until find last statistic block BEGIN...END
    with open(config["impstats_file"]) as file:
        # loop to read iterate from last line
        whole_file = reversed(file.readlines())
        for line in whole_file:
            stat_string = line + stat_string
            result = re.search(stat_block_map, stat_string, re.MULTILINE)
            if result:
                break

    if result:
        tmp_json = {}
        if config["zabbix"]:
            zabbix_json = {}

        matches = re.finditer(stat_json_map, result.group("statistic"), re.MULTILINE)
        for matchNum, match in enumerate(matches, start=1):
            # load json
            try:
                item = json.loads(match.group("json"))
            except ValueError:
                print("Decoding JSON has failed")
                break

            # convert json
            if item["origin"] in config["filter_origin"].keys():
                key = item["origin"]
                if re.search(config["filter_origin"][key], item["name"]):
                    tmp_key = re.sub("[\s\W]+", "-", item["name"])
                    clean_data = json_stat_cleanup(item.copy(), config["stat_keys_del"])

                    # reset counter in case of no updates after stat period
                    timeout = datetime.strptime(match.group("timestamp"), stat_timestamp) + timedelta(seconds=int(config["stat_period"]))
                    if datetime.now() > timeout:
                        reset_counters(clean_data)

                    if key not in tmp_json.keys():
                        tmp_json[key] = []
                    tmp_json[key].append({ tmp_key: clean_data })

                    if config["zabbix"]:
                        zabbix_key = re.sub("[\s\W]+", "_", key)
                        if zabbix_key not in zabbix_json.keys():
                            zabbix_json[zabbix_key] = []

                        zabbix_json[zabbix_key].append( clean_data )
                        last_index = len(zabbix_json[zabbix_key]) - 1
                        zabbix_json[zabbix_key][last_index].update({ "name": tmp_key })

        # convert json to dot-notation
        for _ in iter(json_to_dot(tmp_json)):
            for key, value in _.items():
                metric_path = "{},{}".format(origin, key.replace(".", "-")).replace(",", ".")
                tuples.append((metric_path, (update_time, value)))

        if config["zabbix"]:
            print(json.dumps(zabbix_json, sort_keys=True))

        # send carbon package
        if len(tuples) > 0 :
            pkg = pickle.dumps(tuples, 1)
            pkg_size = struct.pack("!L", len(pkg))

            sock = socket.socket()
            sock.settimeout(10)
            try:
                sock.connect((config["carbon"]["server"], config["carbon"]["port"]))
            except socket.error:
                print("Connection error")
                exit(1)
            sock.sendall(pkg_size)
            sock.sendall(pkg)

if __name__ == "__main__":
    main()