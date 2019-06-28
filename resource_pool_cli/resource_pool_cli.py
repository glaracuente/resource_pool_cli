#!/usr/bin/python3

import click
import sys
import os
import subprocess
import time
import fileinput
import shutil

# Chose to import helper functions as rp to make it easier to understand
# that these rp.* function are defined in another file.
import pool_helpers as rp

# Using the import * here to bring in the DIR varibales
from pool_helpers import *


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    pass


@cli.command("list", short_help="List all pools")
def list():
    for file in os.listdir(POOLS_DIR):
        click.echo(rp.get_pool_info_table(file))


@cli.command("show", short_help="Show pool info")
@click.argument("rp_name")
def show(rp_name):
    rp.verify_rp_name(rp_name)
    click.echo(rp.get_pool_info_table(rp_name))


@cli.command("create", short_help="Create new pool")
@click.argument("rp_name")
@click.option("--cores", "-c", type=int)
@click.option("--memory", "-m", type=int)
def create(rp_name, cores, memory):
    if not cores or not memory:
        click.echo("You must specify cores and memory")
        sys.exit()

    click.echo("Analyzing hardware inventory...")
    fleet_specs = rp.get_specs("fleet")

    total_cores = 0
    total_memory = 0
    masters_list = []
    workers_list = []

    # Pick a server with a high core count to be the master
    highest_core_count = 0
    for server in fleet_specs:
        this_server_cores = fleet_specs[server]["cores"]
        if this_server_cores > highest_core_count:
            highest_core_count = this_server_cores
            masters_list.clear()
            masters_list.append(server)

    # Try to add other servers as workers, until request is met
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

    # Resource fulfilment is assumed, but now we have to verify before moving forward.
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

    # Initialzing the new pool
    rp.init_pool_dir(rp_name)
    rp.init_pool(rp_name, masters_list, workers_list)

    masters_file = "{}/{}/masters.yml".format(POOLS_DIR, rp_name)
    master_server = get_all_servers_in_yaml_file(masters_file)
    master_server = master_server[0]

    # Initialzing the master server, and saving it's unique token and hash
    # because workers will need this to join this cluster
    click.echo("Initializing master server...")
    rp.run_playbook("install_k8s", masters_file)
    kubeadm_init_output = rp.run_playbook("setup_master", masters_file)

    token = kubeadm_init_output.split("--token")[1].split()[0]
    cert_hash = kubeadm_init_output.split("--discovery-token-ca-cert-hash")[1].split()[
        0
    ]

    # Dynamically creating unique join file for this pool, using the token/hash
    # that we got from the master.
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

    # We sleep here, because the workers cannot try to join the master until
    # it is ready, which takes about 30 seconds.
    click.echo("waiting for master to be ready...")
    time.sleep(35)

    click.echo("Joining workers to the master...")
    workers_file = "{}/{}/workers.yml".format(POOLS_DIR, rp_name)
    rp.run_playbook("install_k8s", workers_file)

    # The reason the run_playbook function isn't just called here is
    # because this is the unique join playbook specific to this pool.
    join_cmd = "ansible-playbook {} -i {}".format(join_file, workers_file)
    process = subprocess.Popen(
        join_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    join_cmd_output = str(process.communicate()[0])

    # We sleep again here because the workers take about 10 seconds to be
    # ready, and the dashboard is a k8s service that will need to be
    # deployed to the workers.
    time.sleep(15)
    click.echo("Deploying cluster dashboard...")
    rp.run_playbook("setup_k8s_dashboard", masters_file)


@cli.command("resize", short_help="Change pool specs")
@click.argument("rp_name")
@click.option("--cores", "-c", type=int)
@click.option("--memory", "-m", type=int)
def resize(rp_name, cores, memory):
    rp.verify_rp_name(rp_name)
    if not cores and not memory:
        click.echo("You must specify cores or memory")
        sys.exit()

    total_cores_mem = rp.get_total_cores_mem(rp_name)
    pool_core_count = total_cores_mem[0]
    pool_mem_amount = total_cores_mem[1]

    requested_cores = 0
    requested_mem = 0
    resize_type = "none"
    core_resize_type = "none"
    mem_resize_type = "none"

    # Check whether the user is trying to increase or decrease the cpu/mem
    # If they are trying to increase one and decrease the other, we cannot
    # continue, because this is a more advanced algorithm that will be
    # released in a future version.
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
        click.echo(
            "Your request is invalid. You specified resize parameters that equal the current state of the pool."
        )
        sys.exit()
    else:
        specs = ""
        if resize_type == "increase":
            specs = rp.get_specs("fleet")
        if resize_type == "decrease":
            specs = rp.get_specs(rp_name)

        # The absolute value is used here, which allows the majority of the logic
        # to be used in both the increase and decrease scenarios. This helps to
        # avoid writing duplicate code and too many if/else statements.
        abs_requested_cores = abs(requested_cores)
        abs_requested_mem = abs(requested_mem)

        # Since a physical server will usually have more GB of ram, than # of cores, we sort
        # by cores first, when possible. My thinking here was the case where a user wants to
        # reduce a pool by 24 cores. Let's say we have servers with 12 or 24 cores, and 256 GB
        # of ram. It is better to removes 1x24 cores and 256 GB of ram, instead of 2x12 cores
        # and 512GB of ram.
        if sorter == "cores":
            sorted_specs = sorted(
                specs.items(), key=lambda tup: (tup[1]["cores"]), reverse=True
            )
        if sorter == "memory":
            sorted_specs = sorted(
                specs.items(), key=lambda tup: (tup[1]["mem"]), reverse=True
            )
        if sorter == "both":
            sorted_specs = sorted(
                specs.items(),
                key=lambda tup: (tup[1]["cores"], tup[1]["mem"]),
                reverse=True,
            )

        attempted_core_count = 0
        attempted_mem_count = 0
        attempted_servers_list = []

        # Build a list of servers to meet the request
        for i in sorted_specs:
            if (cores and attempted_core_count < abs_requested_cores) or (
                memory and attempted_mem_count < abs_requested_mem
            ):
                server = i[0]
                specs = i[1]
                server_cores = specs["cores"]
                server_mem = specs["mem"]

                attempted_servers_list.append(server)
                attempted_core_count += server_cores
                attempted_mem_count += server_mem

        # Check if the request can actually be met, and proceed accordingly.
        if (cores and attempted_core_count < abs_requested_cores) or (
            memory and attempted_mem_count < abs_requested_mem
        ):
            if resize_type == "increase":
                click.echo("The requested resources are not available:")
                output_head = "Available"
            if resize_type == "decrease":
                click.echo(
                    "The requested decrease would bring the number of resources below 0, consider using the destroy option:"
                )
                output_head = "Current"
            if cores:
                click.echo("{} cores: {}".format(output_head, attempted_core_count))
                click.echo(
                    "Requested {} in cores: {}".format(
                        resize_type, attempted_core_count
                    )
                )
            if memory:
                click.echo("{} memory: {} GB".format(output_head, attempted_mem_count))
                click.echo(
                    "Requested {} in memory: {} GB".format(
                        resize_type, attempted_mem_count
                    )
                )
        else:
            servers_to_transfer = attempted_servers_list
            if resize_type == "increase":
                final_core_count = pool_core_count + attempted_core_count
                final_mem_amount = pool_mem_amount + attempted_mem_count
            if resize_type == "decrease":
                final_core_count = pool_core_count - attempted_core_count
                final_mem_amount = pool_mem_amount - attempted_mem_count

            # Since cores and GB of memory are coupled together in real physical servers, we can't just add/delete exact numbers
            # of resources. Therefore, the actual final specs may differ, and this can be very destructive when downgrading a pool.
            # This is why we must warn the user here and get their confirmation.
            warning = "Your requested {} may have resulted in a higher or lower number of total resources changes than expected.\n\n \
                       Final core count for {} pool will be: {}\n \
                       Final memory amount for {} pool will be {} GB.\n".format(
                resize_type, rp_name, final_core_count, rp_name, final_mem_amount
            )

            if has_user_confirmed(warning):
                if resize_type == "increase":
                    rp.add_workers_to_pool(rp_name, servers_to_transfer)
                if resize_type == "decrease":
                    rp.return_workers_to_fleet(rp_name, servers_to_transfer)


@cli.command("destroy", short_help="Destroy pool")
@click.argument("rp_name")
def destroy(rp_name):
    rp.verify_rp_name(rp_name)
    warning = "You are attempting to destroy the {} resource pool.\nThis cannot be undone".format(
        rp_name
    )

    if has_user_confirmed(warning):
        masters_yaml_file = "{}/{}/masters.yml".format(POOLS_DIR, rp_name)
        workers_yaml_file = "{}/{}/workers.yml".format(POOLS_DIR, rp_name)

        click.echo("Destroying cluster...")
        rp.run_playbook("reset", masters_yaml_file)
        rp.run_playbook("reset", workers_yaml_file)

        click.echo("Returning servers back to fleet...")
        all_masters_list = get_all_servers_in_yaml_file(masters_yaml_file)
        all_workers_list = get_all_servers_in_yaml_file(workers_yaml_file)

        rp.transfer_servers(all_masters_list, masters_yaml_file, FLEET_HOSTS_YAML_FILE)
        rp.transfer_servers(all_workers_list, workers_yaml_file, FLEET_HOSTS_YAML_FILE)

        click.echo("Cleaning up files...")
        shutil.rmtree("{}/{}".format(POOLS_DIR, rp_name))
    else:
        click.echo("Your input did not match the validation string")


if __name__ == "__main__":
    cli()