provider "aws" {
  region = "us-east-1"
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
              EOF

  tags = {
    Name = "captain"
  }
}

resource "aws_instance" "resource_server_medium" {
  ami           = "ami-01d9d5f6cecc31f85"
  instance_type = "t2.medium"
  count         = 6
  key_name      = "grlaracuente-IAM"

  tags = {
    Name = "resource_server_medium"
  }
}

resource "aws_instance" "resource_server_micro" {
  ami           = "ami-01d9d5f6cecc31f85"
  instance_type = "t2.micro"
  count         = 6
  key_name      = "grlaracuente-IAM"

  tags = {
    Name = "resource_server_micro"
  }
}

output "captain_public_ip" {
  value = ["${aws_instance.captain.public_ip}"]
}

output "resource_server_medium_public_ips" {
  value = ["${aws_instance.resource_server_medium.*.public_ip}"]
}

output "resource_server_micro_public_ips" {
  value = ["${aws_instance.resource_server_micro.*.public_ip}"]
}

