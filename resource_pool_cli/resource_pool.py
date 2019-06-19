#!/usr/bin/python3

import click
import random
import string
import sys
import os
import subprocess
import json
import time
import fileinput
from prettytable import PrettyTable
import yaml
import shutil


ANSIBLE_DIR = "/etc/ansible"
TEMPLATE_DIR = "{}/pool_template".format(ANSIBLE_DIR)
FLEET_HOSTS_YAML_FILE = "{}/fleet/hosts".format(ANSIBLE_DIR)


def init_pool(rp_name):
    shutil.copytree(TEMPLATE_DIR, "{}/{}".format(ANSIBLE_DIR, rp_name))


def get_master(hosts_file):
    with open(hosts_file, "r") as stream:
        try:
            master_server_pair = yaml.safe_load(stream)["all"]["children"]["master"][
                "hosts"
            ]
            for key in master_server_pair:
                master_server = key
        except yaml.YAMLError as exc:
            click.echo(exc)
        except KeyError as key_exc:
            return "None"

    return master_server


def allocate_resources(hosts_file, masters_list, worker_list):
    # removing servers from fleet list
    with open(FLEET_HOSTS_YAML_FILE, "r") as stream:
        try:
            fleet_hosts_yaml = yaml.safe_load(stream)
            servers = masters_list + worker_list
            for server in servers:
                del fleet_hosts_yaml["all"]["hosts"][server]
            updated_fleet_hosts_yaml = fleet_hosts_yaml
        except yaml.YAMLError as exc:
            click.echo(exc)

    with open(FLEET_HOSTS_YAML_FILE, "w") as f:
        yaml.dump(updated_fleet_hosts_yaml, f)

    # adding servers to resource server list
    pool_hosts_yaml_file = hosts_file
    with open(pool_hosts_yaml_file, "r") as stream:
        try:
            pool_hosts_yaml = yaml.safe_load(stream)
            temp_workers_dict = {}
            for worker in worker_list:
                temp_workers_dict[worker] = None
            pool_hosts_yaml['all']['children']['workers']['hosts'] = temp_workers_dict

            temp_masters_dict = {}
            for master in masters_list:
                temp_masters_dict[master] = None
            pool_hosts_yaml['all']['children']['master']['hosts'] = temp_masters_dict
            updated_pool_hosts_yaml = pool_hosts_yaml
        except yaml.YAMLError as exc:
            click.echo(exc)

    with open(pool_hosts_yaml_file, "w") as f:
        yaml.dump(updated_pool_hosts_yaml, f)


def repurpose_resources(hosts_file):
    # removing servers from pool list
    pool_hosts_yaml_file = hosts_file
    returning_servers = []
    with open(pool_hosts_yaml_file, "r") as stream:
        try:
            pool_hosts_yaml = yaml.safe_load(stream)
            workers = pool_hosts_yaml['all']['children']['workers']['hosts']
            for worker in workers:
                returning_servers.append(worker)
            masters = pool_hosts_yaml['all']['children']['master']['hosts']
            for master in masters:
                returning_servers.append(master)
        except yaml.YAMLError as exc:
            click.echo(exc)
    
    # adding servers to resource fleet list
    full_server_list = []
    with open(FLEET_HOSTS_YAML_FILE, "r") as stream:
        try:
            fleet_hosts_yaml = yaml.safe_load(stream)
            temp_servers_dict = {}

            current_fleet_servers = fleet_hosts_yaml["all"]["hosts"]
            for server in current_fleet_servers:
                temp_servers_dict[server] = None

            for server in returning_servers:
                temp_servers_dict[server] = None

            fleet_hosts_yaml["all"]["hosts"] = temp_servers_dict
            updated_fleet_hosts_yaml = fleet_hosts_yaml
        except yaml.YAMLError as exc:
            click.echo(exc)

    with open(FLEET_HOSTS_YAML_FILE, "w") as f:
        yaml.dump(updated_fleet_hosts_yaml, f)
 

def get_specs(rp_name):
    rp_dir = "{}/{}".format(ANSIBLE_DIR, rp_name)

    cmd = "ansible all -i {}/hosts -m gather_facts --tree {}".format(rp_dir, rp_dir)
    process = subprocess.Popen(
        cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out = process.communicate()[0]
    
    specs = {}

    for file in os.listdir(rp_dir):
        if not file.startswith("1"):
            continue

        with open("{}/{}".format(rp_dir, file), "r") as myfile:
            data = myfile.read()
        facts = json.loads(data)

        if "msg" in facts:
            if facts["msg"].startswith("SSH Error"):
                os.remove("{}/{}".format(rp_dir, file))
                continue

        this_server_core_count = facts["ansible_facts"]["ansible_processor_cores"]
        this_server_mem_amount = facts["ansible_facts"]["ansible_memtotal_mb"] / 1024.0
        specs[file] = {"cores": this_server_core_count, "mem": round(this_server_mem_amount)}
        os.remove("{}/{}".format(rp_dir, file))

    return specs


def show_pool_info(rp_name):
    pool_core_count = 0
    pool_mem_amount = 0

    specs = get_specs(rp_name)
    
    hosts_file = "{}/{}/hosts".format(ANSIBLE_DIR, rp_name)
    master_server = get_master(hosts_file)

    for server in specs:
        if server == master_server:
            continue
        this_server_core_count = specs[server]["cores"]
        this_server_mem_amount = specs[server]["mem"]
        pool_core_count = pool_core_count + this_server_core_count
        pool_mem_amount = pool_mem_amount + this_server_mem_amount

    output_table = PrettyTable(["Pool Name", rp_name])
    output_table.add_row(["Cluster Master", master_server])
    output_table.add_row(["CPU Cores", pool_core_count])
    output_table.add_row(["GB of RAM", round(pool_mem_amount, 2)])
    click.echo(output_table)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    pass


@cli.command()
def list():
    for file in os.listdir(ANSIBLE_DIR):
        if not os.path.isdir("{}/{}".format(ANSIBLE_DIR, file)) or file == "pool_template":
            continue
        show_pool_info(file)


@cli.command()
@click.argument("rp_name")
def show(rp_name):
    show_pool_info(rp_name)


@cli.command()
@click.argument("rp_name")
@click.option("--cores", "-c", type=int)
@click.option("--memory", "-m", type=int)
def create(rp_name, cores, memory):
    if not cores or not memory:
        click.echo("You must specify cores and memory")
        sys.exit()

    click.echo("Analyzing hardware inventory...")
    fleet_specs = get_specs("fleet")

    total_cores = 0
    total_memory = 0
    masters_list = []
    workers_list = []

    highest_core_count = 0
    for server in fleet_specs:
        this_server_cores = fleet_specs[server]['cores']
        if this_server_cores > highest_core_count:
            highest_core_count = this_server_cores
            masters_list.clear()
            masters_list.append(server)    

    for server in fleet_specs:
        if server in masters_list:
            continue
        if total_cores < cores or total_memory < memory:
            this_server_cores = fleet_specs[server]['cores']
            total_cores = total_cores + this_server_cores
            this_server_memory = fleet_specs[server]['mem']
            total_memory = total_memory + this_server_memory
            workers_list.append(server)
    
    resources_fulfilled = True

    if total_cores < cores:
        click.echo("There are not enough cores available to create a new resource pool.")
        click.echo("Total cores available: {}".format(total_cores))
        resources_fulfilled = False
    if total_memory < memory:
        click.echo("There is not enough memory available to create a new resource pool.")
        click.echo("Total memory available: {} GB".format(total_memory))
        resources_fulfilled = False

    if not resources_fulfilled:
        sys.exit()

    click.echo("Creating RP with {} cores and {}GB of memory...".format(cores, memory))

    init_pool(rp_name)
    hosts_file = "{}/{}/hosts".format(ANSIBLE_DIR, rp_name)
    allocate_resources(hosts_file, masters_list, workers_list)

    master_server = get_master(hosts_file)

    click.echo("Initializing master server...")
    cmd = "ansible-playbook -i {} /etc/ansible/k8s".format(hosts_file)
    process = subprocess.Popen(
        cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    kubeadm_init_output = str(process.communicate()[0])
    token = kubeadm_init_output.split("--token")[1].split()[0]
    cert_hash = kubeadm_init_output.split("--discovery-token-ca-cert-hash")[1].split()[
        0
    ]

    join_file = "/etc/ansible/{}/join".format(rp_name)
    with fileinput.FileInput(join_file, inplace=True) as file:
        for line in file:
            print(line.replace("MASTERIP", master_server), end="")

    with fileinput.FileInput(join_file, inplace=True) as file:
        for line in file:
            print(
                line.replace(
                    "CREDS",
                    "--token {} --discovery-token-ca-cert-hash {}".format(
                        token, cert_hash
                    ),
                ),
                end="",
            )

    click.echo("waiting for master to be ready...")
    time.sleep(35)
    click.echo("Joining workers to the master...")
    
    cmd = "ansible-playbook {} -i {}".format(join_file, hosts_file)
    process = subprocess.Popen(
        cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    join_output = str(process.communicate()[0])

@cli.command()
@click.option("--cores", "-c", type=int)
@click.option("--memory", "-m", type=int)
def resize(cores, memory):
    if not cores and not memory:
        click.echo("You must specify cores or memory")
    else:
        click.echo("Resizing RP with {} cores and {}GB".format(cores, memory))


@cli.command()
@click.argument("rp_name")
def destroy(rp_name):
    click.echo(
        "You are attempting to destroy the {} resource pool.\nThis cannot be undone".format(
            rp_name
        )
    )
    validation_string = randomString(5)
    click.echo(
        "To confirm this action, please type out the following string: {}".format(
            validation_string
        )
    )

    user_validation_string = input("Enter string : ")

    if user_validation_string == validation_string:
        hosts_file = "{}/{}/hosts".format(ANSIBLE_DIR, rp_name)
        click.echo("Destroying cluster...")
        cmd = "ansible-playbook /etc/ansible/destroy -i {}".format(hosts_file)
        process = subprocess.Popen(
            cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        destroy_output = str(process.communicate()[0])

        click.echo("Returning servers back to fleet...")
        repurpose_resources(hosts_file)
        click.echo("Cleaning up files...")
        shutil.rmtree("{}/{}".format(ANSIBLE_DIR, rp_name))
    else:
        click.echo("Your input did not match the validation string")


def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(stringLength))


if __name__ == "__main__":
    cli()