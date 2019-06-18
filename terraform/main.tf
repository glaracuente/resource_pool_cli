provider "aws" {
  region = "us-east-1"
}

variable "num_of_resource_worker_servers" {
  default = 6
}

resource "aws_instance" "captain" {
  ami           = "ami-01d9d5f6cecc31f85"
  instance_type = "t2.micro"
  key_name      = "grlaracuente-IAM"

  user_data = <<-EOF
              #!/bin/bash
              sudo apt-get update
              sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
              sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -      
              sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
              sudo apt-get update
              sudo apt-get install -y docker-ce docker-ce-cli containerd.io
              sudo curl -X GET https://raw.githubusercontent.com/glaracuente/resourcer/develop/ansible/Dockerfile > /var/tmp/Dockerfile
              sudo docker build /var/tmp/ -t resource_pool
              mkdir  /var/tmp/keys
              mkdir  /var/tmp/ansible
              EOF

  tags = {
    Name = "captain"
  }
}

resource "aws_instance" "resource_server_master" {
  ami           = "ami-01d9d5f6cecc31f85"
  instance_type = "t2.xlarge"
  key_name      = "grlaracuente-IAM"

  user_data = <<-EOF
              #!/bin/bash
              #THIS SHOULD ALL REALLY HAPPEN IN ANSIBLE....SERVER SHOULD JUST NEED TO BE RUNNING UBUNTU
              sudo apt-get update
              sudo apt-get install -y python
              sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
              sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -      
              sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
              sudo apt-get update
              sudo apt-get install -y docker-ce docker-ce-cli containerd.io
              EOF

  tags = {
    Name = "resource_server"
  }
}

resource "aws_instance" "resource_server_worker" {
  ami           = "ami-01d9d5f6cecc31f85"
  instance_type = "t2.micro"
  count         = var.num_of_resource_worker_servers
  key_name      = "grlaracuente-IAM"

  user_data = <<-EOF
              #!/bin/bash
              #THIS SHOULD ALL REALLY HAPPEN IN ANSIBLE....SERVER SHOULD JUST NEED TO BE RUNNING UBUNTU
              sudo apt-get update
              sudo apt-get install -y python
              sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
              sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -      
              sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
              sudo apt-get update
              sudo apt-get install -y docker-ce docker-ce-cli containerd.io
              EOF

  tags = {
    Name = "resource_server"
  }
}

output "captain_public_ip" {
  value = ["${aws_instance.captain.public_ip}"]
}

output "resource_server_master_public_ips" {
  value = ["${aws_instance.resource_server_master.public_ip}"]
}

output "resource_server_worker_public_ips" {
  value = ["${aws_instance.resource_server_worker.*.public_ip}"]
}

#output "resource_server_private_ips" {
#  value = ["${aws_instance.resource_server.*.private_ip_address}"]
#}

