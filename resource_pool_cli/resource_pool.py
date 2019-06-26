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


def verify_rp_name(rp_name):
    is_rp_name_valid = False

    for file in os.listdir(POOLS_DIR):
        if file == rp_name:
            is_rp_name_valid = True
    
    if not is_rp_name_valid:
        click.echo("There is no resource pool named {}.".format(rp_name))
        sys.exit()


def init_pool_dir(rp_name):
    shutil.copytree(TEMPLATE_DIR, "{}/{}".format(POOLS_DIR, rp_name))


def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(stringLength))


def run_playbook(playbook_name, hosts_yaml_file):
    playbook_cmd = "ansible-playbook {}/{}.yml -i {}".format(
        PLAYBOOK_DIR, playbook_name, hosts_yaml_file
    )

    process = subprocess.Popen(
        playbook_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    playbook_cmd_output = str(process.communicate()[0])
   
    return playbook_cmd_output


def transfer_servers(servers_list, from_yaml_file, to_yaml_file):
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


def add_workers_to_pool(rp_name, server_list):
    pool_yaml_file = "{}/{}/workers.yml".format(POOLS_DIR, rp_name)
    transfer_servers(server_list, FLEET_HOSTS_YAML_FILE, pool_yaml_file)
    
    run_playbook("install_k8s", pool_yaml_file)
    join_file = "{}/{}/join.yml".format(POOLS_DIR, rp_name)
    cmd = "ansible-playbook {} -i {}".format(join_file, pool_yaml_file)
    process = subprocess.Popen(
        cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    join_output = str(process.communicate()[0])


def return_workers_to_fleet(rp_name, server_list):
    master_yaml_file = "{}/{}/masters.yml".format(POOLS_DIR, rp_name)
    workers_yaml_file = "{}/{}/workers.yml".format(POOLS_DIR, rp_name)

    for server in server_list:
        node_name = "ip-{}".format(
            server.replace(".", "-")
        )
        cmd = "ansible-playbook {}/drain.yml -i {} --extra-vars node={}".format(
            PLAYBOOK_DIR, master_yaml_file, node_name
        )
        process = subprocess.Popen(
            cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        drain_output = str(process.communicate()[0])

        cmd = "ansible-playbook {}/reset.yml -i {} --limit {}".format(PLAYBOOK_DIR, workers_yaml_file, server)
        process = subprocess.Popen(
            cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        reset_output = str(process.communicate()[0])

    transfer_servers(server_list, workers_yaml_file, FLEET_HOSTS_YAML_FILE)


def get_specs(rp_name):
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


def get_total_cores_mem(rp_name):
    pool_core_count = 0
    pool_mem_amount = 0

    specs = get_specs(rp_name)

    for server in specs:
        this_server_core_count = specs[server]["cores"]
        this_server_mem_amount = specs[server]["mem"]
        pool_core_count += this_server_core_count
        pool_mem_amount += this_server_mem_amount

    return [pool_core_count, round(pool_mem_amount, 2)]


def show_pool_info(rp_name):
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
    verify_rp_name(rp_name)
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
            total_cores += this_server_cores
            this_server_memory = fleet_specs[server]["mem"]
            total_memory += this_server_memory
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

    # formatting unique join file for this pool, since each master has a a unique token/hash required to join it
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
    
    time.sleep(15)
    click.echo("Deploying cluster dashboard...")
    run_playbook("setup_k8s_dashboard", masters_file)


@cli.command()
@click.argument("rp_name")
@click.option("--cores", "-c", type=int)
@click.option("--memory", "-m", type=int)
def resize(rp_name, cores, memory):  #NEED TO REALLY TEST
    verify_rp_name(rp_name)
    if not cores and not memory:
        click.echo("You must specify cores or memory")
        sys.exit()

    total_cores_mem = get_total_cores_mem(rp_name)
    pool_core_count = total_cores_mem[0]
    pool_mem_amount = total_cores_mem[1]

    requested_cores = 0
    requested_mem = 0
    resize_type = "none"
    core_resize_type = "none"
    mem_resize_type = "none"

    if cores:
        requested_cores = cores - pool_core_count
        if requested_cores > 0:
            core_resize_type = "increase"
        elif requested_cores < 0:
            core_resize_type = "decrease"
        resize_type = core_resize_type
        sorter = "cores"
    if memory:
        requested_mem = memory - pool_mem_amount
        if requested_mem > 0:
            mem_resize_type = "increase"
        elif requested_mem < 0:
            mem_resize_type = "decrease"
        resize_type = mem_resize_type
        sorter = "memory"
    if cores and memory:
        if core_resize_type != mem_resize_type:
            click.echo(
                "You have requested to increase one type of resource, and decrease the other. \
                       This feature will not be supported until a future release."
            )
            sys.exit()
        sorter = "both"

    if resize_type == "none":
        click.echo("Your request is invalid. You specified resize parameters that equal the current state of the pool.")
        sys.exit()
    else:
        specs = ""
        if resize_type == "increase":
            specs = get_specs("fleet")
        if resize_type == "decrease":
            specs = get_specs(rp_name)
          
        abs_requested_cores = abs(requested_cores)    
        abs_requested_mem = abs(requested_mem)

        if sorter == "cores":
            sorted_specs = sorted(specs.items(), key = lambda tup: (tup[1]['cores']), reverse=True)
        if sorter == "memory":
            sorted_specs = sorted(specs.items(), key = lambda tup: (tup[1]['mem']), reverse=True)
        if sorter == "both":
            sorted_specs = sorted(specs.items(), key = lambda tup: (tup[1]['cores'], tup[1]['mem']), reverse=True)
    
        attempted_core_count = 0
        attempted_mem_count = 0
        attempted_servers_list = []

        for i in sorted_specs:
            if (cores and attempted_core_count < abs_requested_cores) or (memory and attempted_mem_count < abs_requested_mem):
                server = i[0]
                specs = i[1]
                server_cores = specs['cores']
                server_mem = specs['mem']

                attempted_servers_list.append(server)
                attempted_core_count += server_cores
                attempted_mem_count += server_mem

        if (cores and attempted_core_count < abs_requested_cores) or (memory and attempted_mem_count < abs_requested_mem):
            if resize_type == "increase": 
                click.echo("The requested resources are not available:")
                output_head = "Available" 
            if resize_type == "decrease":
                click.echo("The requested decrease would bring the number of resources below 0, consider using the destroy option:") 
                output_head = "Current"
            if cores:
                click.echo("{} cores: {}".format(output_head, attempted_core_count))
                click.echo("Requested {} in cores: {}".format(resize_type, attempted_core_count))
            if memory:
                click.echo("{} memory: {} GB".format(output_head, attempted_mem_count))
                click.echo("Requested {} in memory: {} GB".format(resize_type, attempted_mem_count))
        else:
            servers_to_transfer = attempted_servers_list
            if resize_type == "increase": 
                final_core_count = pool_core_count + attempted_core_count
                final_mem_amount = pool_mem_amount + attempted_mem_count
            if resize_type == "decrease": 
                final_core_count = pool_core_count - attempted_core_count
                final_mem_amount = pool_mem_amount - attempted_mem_count

            warning = "Your requested {} may have resulted in a higher or lower number of total resources changes than expected.\n\n \
                       Final core count for {} pool will be: {}\n \
                       Final memory amount for {} pool will be {} GB.\n".format(resize_type, rp_name, final_core_count, rp_name, final_mem_amount)
            
            if has_user_confirmed(warning):
                if resize_type == "increase":
                    add_workers_to_pool(rp_name, servers_to_transfer)
                if resize_type == "decrease":
                    return_workers_to_fleet(rp_name, servers_to_transfer)


@cli.command()
@click.argument("rp_name")
def destroy(rp_name):
    verify_rp_name(rp_name)
    warning = "You are attempting to destroy the {} resource pool.\nThis cannot be undone".format(rp_name)

    if has_user_confirmed(warning):
        masters_yaml_file = "{}/{}/masters.yml".format(POOLS_DIR, rp_name)
        workers_yaml_file = "{}/{}/workers.yml".format(POOLS_DIR, rp_name)

        click.echo("Destroying cluster...")
        run_playbook("reset", masters_yaml_file)
        run_playbook("reset", workers_yaml_file)

        click.echo("Returning servers back to fleet...")
        all_masters_list = get_all_servers_in_yaml_file(masters_yaml_file)
        all_workers_list = get_all_servers_in_yaml_file(workers_yaml_file)

        transfer_servers(all_masters_list, masters_yaml_file, FLEET_HOSTS_YAML_FILE)
        transfer_servers(all_workers_list, workers_yaml_file, FLEET_HOSTS_YAML_FILE)

        click.echo("Cleaning up files...")
        shutil.rmtree("{}/{}".format(POOLS_DIR, rp_name))
    else:
        click.echo("Your input did not match the validation string")


if __name__ == "__main__":
    cli()