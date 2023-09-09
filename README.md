**rSyslog impstats configuration**

`
module(load="impstats" interval="300" severity="7" log.syslog="off" log.file="/var/log/impstats.log" Bracketing="on" Format="cee" ResetCounters="on")
`

With proposed rsyslog configuration impstats module will generate stats in cee/json format which will be converted by script to 
 - dot notation format for carbon
 - json zabbix specific format

## Example
impstats output
```
Thu Jul 13 13:45:08 2023: @cee: { "name": "resource-usage", "origin": "impstats", "utime": 6248546926, "stime": 774370471, "maxrss": 75040, "minflt": 1696230, "majflt": 427, "inblock": 45218, "oublock": 32211952, "nvcsw": 45089945, "nivcsw": 301260 }
```
rsyslog has a weird timestamp for impstat with cee format

#### converted to dot notation 
```
<hostname>.<metric_tag>.<origin>.<name>.<key> = <value>
```
where "origin" and "name" are keys from impstats json output
```
hostname.rsyslog.impstats.resource-usage.utime = 6248546926
hostname.rsyslog.impstats.resource-usage.stime = 774370471
hostname.rsyslog.impstats.resource-usage.maxrss = 75040
hostname.rsyslog.impstats.resource-usage.minflt = 1696230
hostname.rsyslog.impstats.resource-usage.majflt = 427
hostname.rsyslog.impstats.resource-usage.inblock = 45218
hostname.rsyslog.impstats.resource-usage.oublock = 32211952
hostname.rsyslog.impstats.resource-usage.nvcsw = 45089945
hostname.rsyslog.impstats.resource-usage.nivcsw = 301260
```
#### zabbix json format
 ...

**Related links**
* https://www.rsyslog.com/rsyslog-statistic-counter/
* https://www.rsyslog.com/rsyslog-statistic-counter-queues/
* https://sematext.com/blog/monitoring-rsyslogs-performance-with-impstats-and-elasticsearch/
* https://dzone.com/articles/monitoring-rsyslog%E2%80%99s



