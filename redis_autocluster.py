import boto
import boto.ec2
import boto.utils
import os
import sys
import subprocess
import socket
import yaml
from time import sleep

default_region = "us-west-2"
env_region = os.environ.get('AWS_DEFAULT_REGION')
if env_region:
    default_region = env_region
my_private_ip = socket.gethostbyname(socket.gethostname())


def verify_nodes_update(instances, master_instance_ip):
    ''' Verify on all nodes master IP is relevant and still exists '''
    ip_list = []
    for instance in instances:
        ip_list.append(instance.private_ip_address)
    for instance in instances:
        print "Verify node {}".format(instance.private_ip_address)
        p = subprocess.Popen(['redis-cli', '-h', instance.private_ip_address, 'info'], stdout=subprocess.PIPE)
        out, err = p.communicate()
        redis_info_dict = get_redis_info(out)

        # Verify master host is update
        if instance.private_ip_address != master_instance_ip:
            if 'Replication' in redis_info_dict.iterkeys() and 'master_host' in redis_info_dict['Replication']:
                master_host_ip = redis_info_dict['Replication']['master_host']
                if master_host_ip not in ip_list:
                    print '{} not exists on new ip list: {}'.format(master_host_ip, ip_list)
                    print 'redis-cli -h '+instance.private_ip_address+' slaveof '+master_instance_ip+' '+redis_port
                    subprocess.call(['redis-cli', '-h', instance.private_ip_address, 'slaveof', master_instance_ip, redis_port])
                    # reset and update sentinel also
                    set_sentinel_master(instance.private_ip_address, master_instance_ip)
                else:
                    print 'master host {} is already exists on node {}'.format(master_host_ip, instance.private_ip_address)
        else:
            # Verify master is no one slave
            print 'redis-cli -h '+master_instance_ip+' slaveof no one'
            subprocess.call(['redis-cli', '-h', master_instance_ip, 'slaveof', 'no', 'one'])
            # reset and update sentinel also
            set_sentinel_master(instance.private_ip_address, master_instance_ip)


def set_sentinel_master(local_ip, master_instance_ip):
    try:
        subprocess.call(['redis-cli', '-p', '26379', '-h', local_ip, 'sentinel', 'remove', 'mymaster'])

        print 'redis-cli -p 26379 -h ' + local_ip + ' sentinel monitor mymaster '+master_instance_ip+' '+redis_port+' 2'
        subprocess.call(['redis-cli', '-p', '26379', '-h', local_ip, 'sentinel', 'monitor', 'mymaster',
                         master_instance_ip, redis_port, '2'])
    except Exception as ex:
        print ex.message


def get_existing_master(instances):
    count = 0
    while count < 3:
        for instance in instances:
            # Get info from each node to find existing master on any machines
            p = subprocess.Popen(['redis-cli', '-h', instance.private_ip_address, 'info'], stdout=subprocess.PIPE)
            out, err = p.communicate()
            redis_info_dict = get_redis_info(out)
            # if found master with existing slaves, connect to him and exit
            if 'Replication' in redis_info_dict.iterkeys():
                connected_slaves = redis_info_dict['Replication']['connected_slaves']
                if connected_slaves != '0':
                    slave_info = redis_info_dict['Replication']['slave0']
                    print 'Machine {} already master of {}'.format(instance.private_ip_address, slave_info)
                    return instance.private_ip_address
        sleep(1)
        count += 1
    return ''


def get_oldest_instance(instances):
    master_instance = None
    for instance in instances:
        if not master_instance:
            master_instance = instance
        elif launch_time_to_int(instance.launch_time) < launch_time_to_int(master_instance.launch_time):
            master_instance = instance
    return master_instance


def launch_time_to_int(string_launchtime):
    return int('{}'.format(string_launchtime).replace('T', '').replace('000Z', '').replace(':', '').replace('-', '')
               .replace('.', ''))


def is_nutcracker_update(instances, yaml_path):
    private_ips_list = []
    for instance in instances:
        private_ips_list.append("{}:6379:1".format(instance.private_ip_address))

    with open(yaml_path, 'r') as f:
        doc = yaml.safe_load(f)

    if doc['redis1']['servers'] == private_ips_list:
        return True

    return False


def set_nutcracker_yml(yaml_path):
    instances = get_running_instances(tag_key, tag_value)
    private_ips_list = []
    for instance in instances:
        private_ips_list.append("{}:6379:1".format(instance.private_ip_address))

    with open(yaml_path, 'r') as f:
        doc = yaml.safe_load(f)
        doc['redis1']['listen'] = my_private_ip + ':22121'
        doc['redis1']['servers'] = private_ips_list
    with open(yaml_path, 'w') as outfile:
        yaml.dump(doc, outfile, default_flow_style=False)


def get_running_instances_by_tag(tag_key, tag_value):
    conn = boto.ec2.connect_to_region(default_region)
    instances = []
    reservations = conn.get_all_instances(
        filters={'instance-state-name': 'running', "tag:" + tag_key: tag_value}
    )
    for reservation in reservations:
        for instance in reservation.instances:
            instances.append(instance)
            instance.tags()

    return instances


def get_running_instances_asg():
    instance_metadata = boto.utils.get_instance_metadata(timeout=1.9, num_retries=1)
    if instance_metadata:
        instance_id = instance_metadata['instance-id']
        region = instance_metadata['placement']['availability-zone'][:-1]
        conn = boto.ec2.connect_to_region(region)
        instances = conn.get_only_instances(instance_ids=[instance_id])
        current_instance = instances[0]
        if 'aws:autoscaling:groupName' in current_instance.tags:
            tag_key = 'aws:autoscaling:groupName'
            tag_value = current_instance.tags['Name']

            reservations = conn.get_all_instances(
                filters={'instance-state-name': 'running', "tag:"+tag_key: tag_value}
            )
            for reservation in reservations:
                for instance in reservation.instances:
                    instances.append(instance)

            return instances


def set_configuration(key, value, file_path='/etc/redis/redis.conf'):
    new_content = ""
    found = False

    with open(file_path, 'r') as f:
        for line in f:
            if line.startswith('# ' + key) or line.startswith('#' + key) or line.startswith(key):
                found = True
                line = key + ' ' + value
                # remove # if exist
                line = line.replace("# ", "").replace("#", "")

            if "\n" not in line:
                line += "\n"

            new_content += line

    if not found:
        new_content += "\n" + key + " " + value
    with open(file_path, 'w') as f:
        f.write(new_content)


def get_redis_info(out):
    redis_info_dict = {}
    current_values = {}
    current_key = ''
    for line in out.split('\n'):
        line = line.replace('\r', '')
        if '# ' in line:
            current_key = line.replace('# ', '')
        elif ':' in line:
            key = line.split(':')[0]
            value = line.split(':')[1]
            current_values[key] = value
        else:
            redis_info_dict[current_key] = current_values
            current_values = {}

    return redis_info_dict


if __name__ == '__main__':
    tag_key = 'Name'
    tag_value = 'redis-tag'
    redis_port = '6379'
    print sys.argv
    for arg in sys.argv:
        if "tag_key=" in arg:
            tag_value = arg.split("tag_key=")[1]
            print "tag_key={}".format(tag_value)
        if "tag_value=" in arg:
            tag_value = arg.split("tag_value=")[1]
            print "tag_value={}".format(tag_value)
        elif "port=" in arg:
            port = arg.split("port=")[1]

    instances = None
    if tag_key and tag_value:
        instances = get_running_instances_by_tag(tag_key, tag_value)
    else:
        instances = get_running_instances_asg()

    twemproxy_conf = '/opt/twemproxy/conf/redis_nutcracker.yml'
    set_nutcracker_yml(twemproxy_conf)
    master_instance_ip = get_existing_master(instances)

    # If existing master not found, search for the oldest instance
    if not master_instance_ip:
        master_instance = get_oldest_instance(instances)
        master_instance_ip = master_instance.private_ip_address

    if my_private_ip != master_instance_ip:
        print 'redis-cli slaveof ' + master_instance_ip + ' ' + redis_port
        subprocess.call(['redis-cli', 'slaveof', master_instance_ip, redis_port])
    else:
        print 'redis-cli slaveof no one'
        subprocess.call(['redis-cli', 'slaveof', 'no', 'one'])

    set_sentinel_master(my_private_ip, master_instance_ip)
    print 'sudo service twemproxy restart'
    subprocess.call(['sudo', 'service', 'twemproxy', 'restart'])

    # verify all nodes are with update master IP
    verify_nodes_update(instances, master_instance_ip)
    while True:
        if tag_key and tag_value:
            instances = get_running_instances_by_tag(tag_key, tag_value)
        else:
            instances = get_running_instances_asg()
        if not is_nutcracker_update(instances, twemproxy_conf):
            print 'update nutcracker'
            set_nutcracker_yml(twemproxy_conf)
            print 'sudo service twemproxy restart'
            subprocess.call(['sudo', 'service', 'twemproxy', 'restart'])
        sleep(60)

    # subprocess.call(['redis-cli', 'cluster', 'meet', instance.private_ip_address, port])
    # nohup redis-server /etc/redis/sentinel.conf --sentinel
    # redis-cli -p 26379 sentinel monitor mymaster 10.210.146.102 6379 2
    # redis-cli -p 26379 sentinel reset mymaster
    # redis-cli -p 26379 sentinel reset *
    # SENTINEL SET
    # redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster
