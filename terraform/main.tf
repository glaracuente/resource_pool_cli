provider "aws" {
  region = "us-east-1"
}

variable "num_of_servers" {
  default = 1
}

resource "aws_instance" "captain" {
  ami           = "ami-01d9d5f6cecc31f85"
  instance_type = "t2.micro"
  count         = "${var.num_of_servers}"
  key_name      = "grlaracuente-IAM"

    user_data = <<EOF
    
    EOF

    inline = [
      "touch /gerry",
      "mkdir /g3",
    ]
  }

  tags {
    Name = "captain"
  }
}
