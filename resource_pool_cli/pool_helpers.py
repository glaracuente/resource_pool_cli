#!/usr/bin/python3

import click
import random
import string
import sys
import os
import subprocess
import json
from prettytable import PrettyTable
import yaml
import shutil

ANSIBLE_DIR = "/etc/ansible"
PLAYBOOK_DIR = "{}/playbooks".format(ANSIBLE_DIR)
TEMPLATE_DIR = "{}/pool_template".format(ANSIBLE_DIR)
POOLS_DIR = "{}/pools".format(ANSIBLE_DIR)
FLEET_HOSTS_YAML_FILE = "{}/pools/fleet/hosts.yml".format(ANSIBLE_DIR)


def verify_rp_name(rp_name):
    """
    This function verifies that a resource pool directory,
    and thus rp_name, exists
    """
    is_rp_name_valid = False

    for file in os.listdir(POOLS_DIR):
        if file == rp_name:
            is_rp_name_valid = True

    if not is_rp_name_valid:
        click.echo("There is no resource pool named {}.".format(rp_name))
        sys.exit()


def init_pool_dir(rp_name):
    """
    This function initializes a new pool directory, with basic 
    template files in place
    """
    shutil.copytree(TEMPLATE_DIR, "{}/{}".format(POOLS_DIR, rp_name))


def randomString(stringLength=10):
    """
    Generate a random string of fixed length
    """
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(stringLength))


def run_playbook(playbook_name, hosts_yaml_file):
    """
    Wrapper function for running playbooks
    """
    playbook_cmd = "ansible-playbook {}/{}.yml -i {}".format(
        PLAYBOOK_DIR, playbook_name, hosts_yaml_file
    )

    process = subprocess.Popen(
        playbook_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    playbook_cmd_output = str(process.communicate()[0])

    return playbook_cmd_output


def transfer_servers(servers_list, from_yaml_file, to_yaml_file):
    """
    Moves given list of servers from one yaml file to the other
    """
    from_rp_name = from_yaml_file.split("/")[-2]
    to_rp_name = to_yaml_file.split("/")[-2]

    click.echo("Removing servers from {}...".format(from_rp_name))
    with open(from_yaml_file, "r") as stream:
        try:
            from_yaml = yaml.safe_load(stream)
            for server in servers_list:
                del from_yaml["all"]["hosts"][server]
            updated_from_yaml = from_yaml
        except yaml.YAMLError as exc:
            click.echo(exc)

    with open(from_yaml_file, "w") as f:
        yaml.dump(updated_from_yaml, f)

    click.echo("Adding servers to {}...".format(to_rp_name))
    with open(to_yaml_file, "r") as stream:
        try:
            to_yaml = yaml.safe_load(stream)
            temp_servers_dict = {}

            current_servers = to_yaml["all"]["hosts"]
            if current_servers:
                for server in current_servers:
                    temp_servers_dict[server] = None

            for server in servers_list:
                temp_servers_dict[server] = None

            to_yaml["all"]["hosts"] = temp_servers_dict
            updated_to_yaml = to_yaml

        except yaml.YAMLError as exc:
            click.echo(exc)

    with open(to_yaml_file, "w") as f:
        yaml.dump(updated_to_yaml, f)


def has_user_confirmed(warning):
    """
    Prompts user to enter the given random string, and then
    returns a boolean based on matching user input
    """
    click.echo(warning)
    validation_string = randomString(5)
    click.echo(
        "To confirm this action, please type out the following string: {}".format(
            validation_string
        )
    )

    user_validation_string = input("Enter string : ")

    if user_validation_string == validation_string:
        return True
    else:
        return False


def get_all_servers_in_yaml_file(yaml_file):
    """
    Quick extraction of all servers in a hosts yaml file
    """
    all_servers_in_yaml_file = []

    with open(yaml_file, "r") as stream:
        try:
            servers_yaml = yaml.safe_load(stream)
            servers_list = servers_yaml["all"]["hosts"]
            for server in servers_list:
                all_servers_in_yaml_file.append(server)
        except FileNotFoundError as fnfe:
            click.echo("{} does not exist".format(yaml_file))
            sys.exit()
        except yaml.YAMLError as exc:
            click.echo(exc)

    return all_servers_in_yaml_file


def init_pool(rp_name, masters_list, workers_list):
    """
    Initial transfer of servers into a new pool
    """
    masters_yaml_file = "{}/{}/masters.yml".format(POOLS_DIR, rp_name)
    transfer_servers(masters_list, FLEET_HOSTS_YAML_FILE, masters_yaml_file)

    workers_yaml_file = "{}/{}/workers.yml".format(POOLS_DIR, rp_name)
    transfer_servers(workers_list, FLEET_HOSTS_YAML_FILE, workers_yaml_file)


def add_workers_to_pool(rp_name, server_list):
    """
    1) Adds new worker nodes to an existing pool. 
    2) Makes sure kubernetes is installed on each new server.
    3) Joins them to the master as worker nodes
    """
    pool_yaml_file = "{}/{}/workers.yml".format(POOLS_DIR, rp_name)
    transfer_servers(server_list, FLEET_HOSTS_YAML_FILE, pool_yaml_file)

    run_playbook("install_k8s", pool_yaml_file)

    # The reason the run_playbook function isn't just called here is
    # because this is a unique join playbook specific to this pool.
    join_file = "{}/{}/join.yml".format(POOLS_DIR, rp_name)
    cmd = "ansible-playbook {} -i {}".format(join_file, pool_yaml_file)

    process = subprocess.Popen(
        cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    join_output = str(process.communicate()[0])


def return_workers_to_fleet(rp_name, server_list):
    """
    1) Drains nodes and deletes them from the k8s cluster (done from master).
    2) Resets kubeadm state on the nodes (done from nodes themselves).
    3) Moves servers back into the fleet.

    run_playbook() is not used in this block of code because these playbook
    commands utilize extra arguments such as --extra-vars and --limit, which
    are needed here, but not widely used in the rest of the code. 
    """
    master_yaml_file = "{}/{}/masters.yml".format(POOLS_DIR, rp_name)
    workers_yaml_file = "{}/{}/workers.yml".format(POOLS_DIR, rp_name)

    for server in server_list:
        node_name = "ip-{}".format(server.replace(".", "-"))
        cmd = "ansible-playbook {}/drain.yml -i {} --extra-vars node={}".format(
            PLAYBOOK_DIR, master_yaml_file, node_name
        )
        process = subprocess.Popen(
            cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        drain_output = str(process.communicate()[0])

        cmd = "ansible-playbook {}/reset.yml -i {} --limit {}".format(
            PLAYBOOK_DIR, workers_yaml_file, server
        )
        process = subprocess.Popen(
            cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        reset_output = str(process.communicate()[0])

    transfer_servers(server_list, workers_yaml_file, FLEET_HOSTS_YAML_FILE)


def get_specs(rp_name):
    """
    Returns a dictionary with all servers, along with their specs.
    The keys to the dictonary are the server names/ips.
    The values are dictionaries containing the cpu and mem totals. 
    """
    rp_dir = "{}/{}".format(POOLS_DIR, rp_name)
    server_file_name = "workers.yml"

    if rp_name == "fleet":
        server_file_name = "hosts.yml"

    ansible_facts_cmd = "ansible all -i {}/{} -m gather_facts --tree {}".format(
        rp_dir, server_file_name, rp_dir
    )
    process = subprocess.Popen(
        ansible_facts_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    ansible_facts_cmd_out = process.communicate()[0]

    specs = {}

    # The ansible_facts_cmd saves facts as json inside of files named after the server.
    # This is why we are looping through the directory, and reading file contents as json.
    for file in os.listdir(rp_dir):
        if file.endswith(".yml"):
            continue

        with open("{}/{}".format(rp_dir, file), "r") as myfile:
            data = myfile.read()
        facts = json.loads(data)

        # Whether or not a server can be reached, the fact file is generated.
        # Here, we remove facts from servers that cannot be reachced,
        # in order to avoid inaccurate spec counts.
        if "msg" in facts:
            if facts["msg"].startswith("SSH Error"):
                os.remove("{}/{}".format(rp_dir, file))
                continue

        this_server_core_count = facts["ansible_facts"]["ansible_processor_cores"]
        this_server_mem_amount = facts["ansible_facts"]["ansible_memtotal_mb"] / 1024.0
        specs[file] = {
            "cores": this_server_core_count,
            "mem": round(this_server_mem_amount),
        }
        os.remove("{}/{}".format(rp_dir, file))

    return specs


def get_total_cores_mem(rp_name):
    """
    While get_specs() returns a dictionary, it is also common that
    we want to know the total amount of cores and memory in a pool.
    This function returns those 2 totals.
    """
    pool_core_count = 0
    pool_mem_amount = 0

    specs = get_specs(rp_name)

    for server in specs:
        this_server_core_count = specs[server]["cores"]
        this_server_mem_amount = specs[server]["mem"]
        pool_core_count += this_server_core_count
        pool_mem_amount += this_server_mem_amount

    return [pool_core_count, round(pool_mem_amount, 2)]


def get_pool_info_table(rp_name):
    """
    This returns a nicely formatted representation of a pool.
    """
    total_cores_mem = get_total_cores_mem(rp_name)
    pool_core_count = total_cores_mem[0]
    pool_mem_amount = total_cores_mem[1]

    if rp_name == "fleet":
        master_server = "N/A"
    else:
        master_server = get_all_servers_in_yaml_file(
            "{}/{}/masters.yml".format(POOLS_DIR, rp_name)
        )[0]

    output_table = PrettyTable(["Pool Name", rp_name])
    output_table.add_row(["Cluster Master", master_server])
    output_table.add_row(["CPU Cores", pool_core_count])
    output_table.add_row(["GB of RAM", pool_mem_amount])
    return output_table