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
PLAYBOOK_DIR = "{}/playbooks".format(ANSIBLE_DIR)
TEMPLATE_DIR = "{}/pool_template".format(ANSIBLE_DIR)
POOLS_DIR = "{}/pools".format(ANSIBLE_DIR)
FLEET_HOSTS_YAML_FILE = "{}/pools/fleet/hosts.yml".format(ANSIBLE_DIR)


def init_pool_dir(rp_name):
    shutil.copytree(TEMPLATE_DIR, "{}/{}".format(POOLS_DIR, rp_name))


def run_playbook(playbook_name, hosts_yaml_file):
    playbook_cmd = "ansible-playbook {}/{}.yml -i {}".format(PLAYBOOK_DIR, playbook_name, hosts_yaml_file)
   
    process = subprocess.Popen(
        playbook_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    playbook_cmd_output = str(process.communicate()[0])
    print(playbook_cmd_output)
    return playbook_cmd_output


def transfer_servers(servers_list, from_yaml_file, to_yaml_file):
    from_rp_name = from_yaml_file.split('/')[-2]
    to_rp_name = to_yaml_file.split('/')[-2]

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


def get_all_servers_in_yaml_file(yaml_file):
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
    masters_yaml_file = "{}/{}/masters.yml".format(POOLS_DIR, rp_name)
    transfer_servers(masters_list, FLEET_HOSTS_YAML_FILE, masters_yaml_file)
   
    workers_yaml_file = "{}/{}/workers.yml".format(POOLS_DIR, rp_name)
    transfer_servers(workers_list, FLEET_HOSTS_YAML_FILE, workers_yaml_file)


def resize_add_servers_to_pool(rp_name, server_list):  # NEED TO WORK FOR MEMORY ALSO # NEED TO SEPARATE THIS INTO JUST PLAYBOOK CALLS, AND UTILITIZE NEW TRANSFER FUNCTION
    # move servers from fleet yaml to pool yaml
    click.echo("removing servers from fleet...")
    with open(FLEET_HOSTS_YAML_FILE, "r") as stream:
        try:
            fleet_hosts_yaml = yaml.safe_load(stream)
            for server in server_list:
                del fleet_hosts_yaml["all"]["hosts"][server]
            updated_fleet_hosts_yaml = fleet_hosts_yaml
        except yaml.YAMLError as exc:
            click.echo(exc)

    with open(FLEET_HOSTS_YAML_FILE, "w") as f:
        yaml.dump(updated_fleet_hosts_yaml, f)

    # adding servers to resource pool
    click.echo("adding servers to {}...".format(rp_name))
    pool_hosts_yaml_file = "{}/{}/hosts".format(ANSIBLE_DIR, rp_name)
    with open(pool_hosts_yaml_file, "r") as stream:
        try:
            pool_hosts_yaml = yaml.safe_load(stream)
            workers_dict = pool_hosts_yaml["all"]["children"]["workers"]["hosts"]
            for worker in server_list:
                workers_dict[worker] = None
            pool_hosts_yaml["all"]["children"]["workers"]["hosts"] = workers_dict

            updated_pool_hosts_yaml = pool_hosts_yaml
        except yaml.YAMLError as exc:
            click.echo(exc)

    with open(pool_hosts_yaml_file, "w") as f:
        yaml.dump(updated_pool_hosts_yaml, f)

    #NEED TO RUN INSTALL KUBE STUFF FIRST....NEED TO BREAK OUT INTO SEPERATE PLAYBOOK
    # NEED..might also be easier to separate workers and master into diff files
    join_file = "{}/{}/join".format(ANSIBLE_DIR, rp_name)
    hosts_file = pool_hosts_yaml_file
    cmd = "ansible-playbook {} -i {}".format(join_file, hosts_file)
    process = subprocess.Popen(
        cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    join_output = str(process.communicate()[0])


def resize_return_servers_to_fleet(hosts_file, server_list): #NEED TO SEPARATE THIS INTO JUST PLAYBOOK CALLS, AND UTILITIZE NEW TRANSFER FUNCTION
    # Need to make this more scalable, not do one node at a time
    hosts_file = "{}/{}/hosts".format(POOLS_DIR, rp_name)
    for server in server_list:
        node_name = "ip-{}".format(
            server.replace(".", "-")
        )  # This may be diff if using hostnames
        cmd = "ansible-playbook {}/drain -i {} --extra-vars node={}".format(
            ANSIBLE_DIR, hosts_file, node_name
        )
        process = subprocess.Popen(
            cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        drain_output = str(process.communicate()[0])

        cmd = "ansible-playbook -i {} --limit {} destroy".format(hosts_file, server)
        process = subprocess.Popen(
            cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        destroy_output = str(process.communicate()[0])

    # then move servers from pool to fleet yaml...SHOULD JUST BE FUNCTION TO MOVE FROM ONE YAML TO OTHER
    # removing servers from pool list
    click.echo("removing servers from {}...".format(rp_name))
    pool_hosts_yaml_file = hosts_file
    with open(pool_hosts_yaml_file, "r") as stream:
        try:
            pool_hosts_yaml = yaml.safe_load(stream)
            for server in server_list:
                del pool_hosts_yaml["all"]["children"]["workers"]["hosts"][server]
            updated_pool_hosts_yaml = pool_hosts_yaml
        except yaml.YAMLError as exc:
            click.echo(exc)

    with open(pool_hosts_yaml_file, "w") as f:
        yaml.dump(updated_pool_hosts_yaml, f)

    # adding servers to fleet 
    click.echo("Adding servers to fleet...")
    with open(FLEET_HOSTS_YAML_FILE, "r") as stream:
        try:
            fleet_hosts_yaml = yaml.safe_load(stream)
            temp_servers_dict = {}

            current_fleet_servers = fleet_hosts_yaml["all"]["hosts"]
            for server in current_fleet_servers:
                temp_servers_dict[server] = None

            for server in server_list:
                temp_servers_dict[server] = None

            fleet_hosts_yaml["all"]["hosts"] = temp_servers_dict
            updated_fleet_hosts_yaml = fleet_hosts_yaml
        except yaml.YAMLError as exc:
            click.echo(exc)

    with open(FLEET_HOSTS_YAML_FILE, "w") as f:
        yaml.dump(updated_fleet_hosts_yaml, f)


def get_specs(rp_name):
    rp_dir = "{}/{}".format(POOLS_DIR, rp_name)
    server_file_name = "workers.yml"

    if rp_name == "fleet":
        server_file_name = "hosts.yml"

    ansible_facts_cmd = "ansible all -i {}/{} -m gather_facts --tree {}".format(rp_dir, server_file_name, rp_dir)
    process = subprocess.Popen(
        ansible_facts_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    ansible_facts_cmd_out = process.communicate()[0]

    specs = {}

    # the ansible_facts_cmd saves facts as files named as the server
    for file in os.listdir(rp_dir):
        if file.endswith(".yml"):
            continue

        with open("{}/{}".format(rp_dir, file), "r") as myfile:
            data = myfile.read()
        facts = json.loads(data)

        # removes facts from server that cannot be reachced, in order to produce accurate spec counts
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


def show_pool_info(rp_name):
    pool_core_count = 0
    pool_mem_amount = 0

    specs = get_specs(rp_name)

    if rp_name == "fleet":
        master_server = "N/A"
    else:
        master_server = get_all_servers_in_yaml_file("{}/{}/masters".format(POOLS_DIR, rp_name))

    for server in specs:
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
    for file in os.listdir(POOLS_DIR):
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
        this_server_cores = fleet_specs[server]["cores"]
        if this_server_cores > highest_core_count:
            highest_core_count = this_server_cores
            masters_list.clear()
            masters_list.append(server)

    for server in fleet_specs:
        if server in masters_list:
            continue
        if total_cores < cores or total_memory < memory:
            this_server_cores = fleet_specs[server]["cores"]
            total_cores = total_cores + this_server_cores
            this_server_memory = fleet_specs[server]["mem"]
            total_memory = total_memory + this_server_memory
            workers_list.append(server)

    resources_fulfilled = True

    if total_cores < cores:
        click.echo(
            "There are not enough cores available to create a new resource pool."
        )
        click.echo("Total cores available: {}".format(total_cores))
        resources_fulfilled = False
    if total_memory < memory:
        click.echo(
            "There is not enough memory available to create a new resource pool."
        )
        click.echo("Total memory available: {} GB".format(total_memory))
        resources_fulfilled = False

    if not resources_fulfilled:
        sys.exit()

    click.echo("Creating RP with {} cores and {}GB of memory...".format(cores, memory))

    init_pool_dir(rp_name)
    init_pool(rp_name, masters_list, workers_list)

    masters_file = "{}/{}/masters.yml".format(POOLS_DIR, rp_name)
    master_server = get_all_servers_in_yaml_file(masters_file)
    master_server = master_server[0]
    
    click.echo("Initializing master server...")
    run_playbook("install_k8s", masters_file)
    kubeadm_init_output = run_playbook("setup_master", masters_file)

    token = kubeadm_init_output.split("--token")[1].split()[0]
    cert_hash = kubeadm_init_output.split("--discovery-token-ca-cert-hash")[1].split()[
        0
    ]

    #formatting unique join file for this pool, since each master has a a unique token/hash required to join it
    join_file = "{}/{}/join.yml".format(POOLS_DIR, rp_name)
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
    workers_file = "{}/{}/workers.yml".format(POOLS_DIR, rp_name)
    run_playbook("install_k8s", workers_file)
    join_cmd = "ansible-playbook {} -i {}".format(join_file, workers_file)
    process = subprocess.Popen(
        join_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    join_cmd_output = str(process.communicate()[0])
    print(join_cmd_output)


@cli.command()
@click.argument("rp_name")
@click.option("--cores", "-c", type=int)
@click.option("--memory", "-m", type=int)
def resize(rp_name, cores, memory):
    if not cores and not memory:
        click.echo("You must specify cores or memory")
        sys.exit()

    # DID THIS EXACT PROCEDURE BEFORE...SHOULD BE WRAPPED IN A FUNCTION
    pool_core_count = 0
    pool_mem_amount = 0

    pool_specs = get_specs(rp_name)

    hosts_file = "{}/{}/hosts".format(ANSIBLE_DIR, rp_name)
    master_server = get_master(hosts_file)

    for server in pool_specs:
        if server == master_server:
            continue
        this_server_core_count = pool_specs[server]["cores"]
        this_server_mem_amount = pool_specs[server]["mem"]
        pool_core_count = pool_core_count + this_server_core_count
        pool_mem_amount = pool_mem_amount + this_server_mem_amount
    #############

    if cores:
        if cores > pool_core_count:
            click.echo("Gathering resources to increase core count...")
            # THIS IS ALSO DONE ALREADY IN CREATE, AND SHOULD JUST BE A FUNCTION
            click.echo("Analyzing hardware inventory...")
            fleet_specs = get_specs("fleet")

            requested_cores = cores - pool_core_count
            new_cores = 0
            workers_list = []

            for server in fleet_specs:
                if new_cores < requested_cores:
                    this_server_cores = fleet_specs[server]["cores"]
                    new_cores = new_cores + this_server_cores
                    workers_list.append(server)

            if requested_cores < new_cores:
                click.echo(
                    "There are not enough cores available to create a new resource pool."
                )
                click.echo("Total cores available: {}".format(new_cores))
                sys.exit()

            click.echo(
                "Resources are available and being migrated into the {} pool...".format(
                    rp_name
                )
            )
            add_servers_to_pool(rp_name, workers_list)

        elif cores < pool_core_count:
            click.echo("Removing resources to decrease core count...")

            cores_to_remove = pool_core_count - cores

            cores_staged_to_remove = 0
            workers_list = []

            for server in pool_specs:
                if cores_staged_to_remove < cores_to_remove:
                    this_server_cores = pool_specs[server]["cores"]
                    cores_staged_to_remove = cores_staged_to_remove + this_server_cores
                    workers_list.append(server)

            remove_servers_from_pool(rp_name, workers_list)
        else:
            click.echo(
                "Requested core count would not change the current pool resources."
            )

    if memory:
        if memory > pool_mem_amount:
            click.echo("Gathering resources to increase memory...")
        elif memory < pool_mem_amount:
            click.echo("Removing resources to decrease memory...")
        else:
            click.echo("Requested memory would not change the current pool resources.")


@cli.command()
@click.argument("rp_name")
def destroy(rp_name): # Still need to protect user against wrong rp_name...should make this a function to inject into every main function
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
        masters_yaml_file = "{}/{}/masters.yml".format(POOLS_DIR, rp_name)
        workers_yaml_file = "{}/{}/workers.yml".format(POOLS_DIR, rp_name)

        click.echo("Destroying cluster...")
        run_playbook("reset", masters_yaml_file)
        run_playbook("reset", masters_yaml_file)
        
        click.echo("Returning servers back to fleet...")
        all_masters_list = get_all_servers_in_yaml_file(masters_yaml_file)
        all_workers_list = get_all_servers_in_yaml_file(workers_yaml_file)

        transfer_servers(all_masters_list, masters_yaml_file, FLEET_HOSTS_YAML_FILE)
        transfer_servers(all_workers_list, workers_yaml_file, FLEET_HOSTS_YAML_FILE)

        click.echo("Cleaning up files...")
        shutil.rmtree("{}/{}".format(POOLS_DIR, rp_name))
    else:
        click.echo("Your input did not match the validation string")


def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(stringLength))


if __name__ == "__main__":
    cli()