provider "aws" {
  region = "${var.aws_region}"
}

output "redis_ami_out" {
  value = "${aws_ami_from_instance.redis_ami.id}"
}

resource "aws_ami_from_instance" "redis_ami" {
  name               = "redis_ami"
  source_instance_id = "${aws_instance.base_instance.id}"
  depends_on = ["aws_instance.base_instance"]
}

resource "aws_instance" "base_instance" {
  ami           = "${lookup(var.aws_base_amis, var.aws_region)}"
  instance_type = "t2.micro"
  key_name      = "${var.key_name}"
  associate_public_ip_address = "${var.public_ip_address}"
  subnet_id     = "${var.subnet_id}"
  security_groups = ["${aws_security_group.ssh_sg.id}"]

  tags {
    Name = "${var.tag_name}"
  }
  provisioner "local-exec" {
    command = "sleep 150 && ansible-playbook -i ${aws_instance.base_instance.private_ip}, -e variable_host=${aws_instance.base_instance.private_ip} --private-key ~/.ssh/${var.key_name}.pem -u ubuntu install_redis.yml"
  }
}

resource "aws_security_group" "ssh_sg" {
  name        = "temp redis sg for image"
  description = "Used to create new image"
  vpc_id      = "${var.vpc_id}"

  # SSH access from anywhere
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  # outbound internet access
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}