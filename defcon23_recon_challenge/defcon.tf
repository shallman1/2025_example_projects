provider "aws" {
  region                  = "us-east-1"
  access_key              = "aws_access"
  secret_key              = "aws_secret"
  # session_token           = "YOUR_SESSION_TOKEN"
}

variable "ami_id" {
  description = "The AMI ID for the instances"
  default     = "ami-08a52ddb321b32a8c"
}

variable "instance_type" {
  description = "Instance type for the EC2 instances"
  default     = "t2.micro"
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "main" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "r" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
}

resource "aws_route_table_association" "a" {
  subnet_id      = aws_subnet.main.id
  route_table_id = aws_route_table.r.id
}

resource "aws_security_group" "sg" {
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "tls_private_key" "example" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "generated_key" {
  key_name   = "ssh"
  public_key = tls_private_key.example.public_key_openssh
}


resource "aws_instance" "ctf" {
  count                       = 60
  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.main.id
  vpc_security_group_ids      = [aws_security_group.sg.id]
  key_name                    = aws_key_pair.generated_key.key_name
  associate_public_ip_address = true
  private_ip                  = "10.0.1.${71 + count.index}"
}

output "instance_public_ips" {
  value       = aws_instance.ctf[*].public_ip
  description = "Public IP addresses of the EC2 instances"
}

resource "local_file" "ec2ips" {
  content  = join("\n", aws_instance.ctf[*].public_ip)
  filename = "${path.module}/ec2ip.csv"
}

output "private_key" {
  value     = tls_private_key.example.private_key_pem
  sensitive = true
}

resource "local_file" "private_key" {
  sensitive_content = tls_private_key.example.private_key_pem
  filename          = "${path.module}/private_key.pem"
}
