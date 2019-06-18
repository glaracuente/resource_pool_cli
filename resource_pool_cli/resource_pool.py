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


ANSIBLE_DIR = "/etc/ansible"
fleet_hosts_yaml_file = "{}/fleet/hosts".format(ANSIBLE_DIR)


def get_master(hosts_file):
    master_server = "unknown"

    with open(hosts_file, "r") as stream:
        try:
            master_server_pair = yaml.safe_load(stream)["all"]["children"]["master"][
                "hosts"
            ]
            for key in master_server_pair:
                master_server = key
        except yaml.YAMLError as exc:
            print(exc)

    return master_server


def allocate_resources(hosts_file, masters_list, worker_list):
    # removing servers from fleet list
    with open(fleet_hosts_yaml_file, "r") as stream:
        try:
            hosts = yaml.safe_load(stream)
            servers = masters_list + worker_list
            for server in servers:
                del hosts["all"]["hosts"][server]
            updated_fleet_hosts_yaml = hosts
        except yaml.YAMLError as exc:
            print(exc)

    with open(fleet_hosts_yaml_file, "w") as f:
        yaml.dump(updated_fleet_hosts_yaml, f)

    # adding servers to resource server list
    pool_hosts_yaml_file = hosts_file
    with open(pool_hosts_yaml_file, "r") as stream:
        try:
            hosts = yaml.safe_load(stream)
            temp_workers_dict = {}
            for worker in worker_list:
                temp_workers_dict[worker] = None
            hosts['all']['children']['workers']['hosts'] = temp_workers_dict

            temp_masters_dict = {}
            for master in masters_list:
                temp_masters_dict[master] = None
            hosts['all']['children']['master']['hosts'] = temp_masters_dict
            updated_pool_hosts_yaml = hosts
        except yaml.YAMLError as exc:
            print(exc)

    with open(pool_hosts_yaml_file, "w") as f:
        yaml.dump(updated_pool_hosts_yaml, f)


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
        specs[file] = {"cores": this_server_core_count, "mem": this_server_mem_amount}
        os.remove("{}/{}".format(rp_dir, file))

    return specs


def show_pool_info(rp_name):
    pool_core_count = 0
    pool_mem_amount = 0

    specs = get_specs(rp_name)

    for server in specs:
        this_server_core_count = specs[server]["cores"]
        this_server_mem_amount = specs[server]["mem"]
        pool_core_count = pool_core_count + this_server_core_count
        pool_mem_amount = pool_mem_amount + this_server_mem_amount

    hosts_file = "{}/{}/hosts".format(ANSIBLE_DIR, rp_name)
    master_server = get_master(hosts_file)

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
    show_specs()
    """
    for file in os.listdir(ANSIBLE_DIR):
        if not os.path.isdir(file):
            continue
        show_pool_info(file)
    """


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
    else:
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
            if total_cores < cores:
                this_server_cores = fleet_specs[server]['cores']
                this_server_memory = fleet_specs[server]['mem']
                total_cores = total_cores + this_server_cores
                total_memory = total_memory + this_server_memory
                workers_list.append(server)
        
        if total_cores < cores:
            click.echo("There are not enough cores available to create a new resource pool.")
            click.echo("Total cores available: {}".format(total_cores))
            sys.exit()
        #if total_memory < memory:
            #click.echo("There is not enough memory available to create a new resource pool.")
            #click.echo("Total memory available: {}".format(total_memory))
            #sys.exit()
        print(masters_list)
        print(workers_list)

        click.echo("Creating RP with {} cores and {}GB of memory".format(cores, memory))


'''
    hosts_file = "{}/{}/hosts".format(ANSIBLE_DIR, rp_name)
    master_server = get_master(hosts_file)

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

    cmd = "ansible-playbook {} -i {}".format(join_file, hosts_file)
    click.echo("waiting for master to be ready...sleeping 40 seconds")
    time.sleep(40)
    click.echo("done sleeping")
    process = subprocess.Popen(
        cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    join_output = str(process.communicate()[0])
'''

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
        cmd = "ansible-playbook /etc/ansible/destroy -i {}".format(hosts_file)
        process = subprocess.Popen(
            cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        destroy_output = str(process.communicate()[0])
        print(destroy_output)
    else:
        click.echo("Your input did not match the validation string")


def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(stringLength))


if __name__ == "__main__":
    cli()