import json
from ssh import ssh_pool_global
from datetime import datetime


# Python script to query runtime statistics
QUERY_CMD = """/usr/bin/python3 -c "
import io, json, psutil, gpustat
fp = io.StringIO()
stat = gpustat.GPUStatCollection.new_query().print_json(fp)
fp.seek(0)
stat = json.loads(fp.read())
stat[\\"cpu_percent\\"] = psutil.cpu_percent(interval=0.1)
stat[\\"mem_percent\\"] = psutil.virtual_memory()[2]
stat[\\"mem_total\\"] = psutil.virtual_memory()[0] / 1024.0 ** 3
print(json.dumps(stat))"
"""


# Query each server and report statistics in markdown
def query(server_list, logger):
    stat_md = '<center>\n\n'
    stat_md += '# Server Statistics\n\n'
    stat_md += '### %s\n\n' % datetime.isoformat(datetime.now(), sep=' ', timespec='seconds')
    stat_md += '</center>\n\n'

    logger.info('Querying %d hosts...' % len(server_list))

    for username, hostname, port in server_list:
        stat_md += '<br><br>\n\n'

        sess = None
        try:
            sess = ssh_pool_global.get(username, hostname, port, logger)
            _, stdout, _ = sess.exec_command(QUERY_CMD, timeout=10)
            server_stat = json.load(stdout)
        except:
            ssh_pool_global.mark_broken(sess)
            logger.info('Failed to connect to %s:%d' % (hostname, port))
            stat_md += '<span style="color:black">**' + \
                'Failed to retrieve statistics for ' + \
                '`%s@%s:%d`' % (username, hostname, port) + \
                '**</span>\n\n'
            continue

        logger.info('Statistics of %s:%d: CPU: %s%%; MEM: %s%%' % (
            hostname, port, server_stat['cpu_percent'], server_stat['mem_percent']
        ))

        # CPU statistics
        stat_md += ('| SSH | Hostname | CPU Load | Memory |\n')
        stat_md += ('|:---:|:--------:|---------:|-------:|\n')
        stat_md += ('|`%s`|`%s`|**%s%%**|**%d** / %d GB|\n' % (
            '%s@%s:%d' % (username, hostname, port),
            server_stat['hostname'],
            server_stat['cpu_percent'],
            server_stat['mem_percent'] * server_stat['mem_total'] / 100.0,
            int(server_stat['mem_total'])
        ))
        stat_md += ('\n')

        # GPU statistics
        stat_md += ('| GPU | Name | Temp | Load | Power | Memory | Processes |\n')
        stat_md += ('|:---:|:----:|-----:|-----:|------:|-------:|----------:|\n')
        for gpu_stat in server_stat['gpus']:
            try:
                if gpu_stat['utilization.gpu'] is None:  # utilization.gpu is `None` on WSL
                    gpu_stat['utilization.gpu'] = 'N/A'
                else:
                    gpu_stat['utilization.gpu'] = '%s%%' % gpu_stat['utilization.gpu']
            except Exception as e:
                logger.error(str(e))
                continue

            try:
                stat_md += ("|%d|%s|%d'C|**%s**|**%d** / %d W|**%d** / %d MB|" % (
                    gpu_stat['index'],
                    gpu_stat['name'],
                    gpu_stat['temperature.gpu'],
                    gpu_stat['utilization.gpu'],
                    gpu_stat['power.draw'],
                    gpu_stat['enforced.power.limit'],
                    gpu_stat['memory.used'],
                    gpu_stat['memory.total']
                ))
            except Exception as e:
                logger.error(str(e))
                continue
            # For gpustat > 0.6.0, idle gpu server will return gpu_stat['process'] = None
            if gpu_stat['processes'] is None:
                gpu_stat['processes'] = []

            for p in gpu_stat['processes']:
                try:
                    stat_md += (" **%s**(%sM) " % (
                        p['username'],
                        p['gpu_memory_usage']
                    ))
                except Exception as e:
                    logger.error(str(e))

            stat_md += ('|\n')

        stat_md += ('\n')

    return stat_md
