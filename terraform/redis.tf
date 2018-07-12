# Specify the provider and access details
provider "aws" {
  region = "${var.aws_region}"
}

resource "aws_elb" "redis-elb" {
  name = "redis-elb-${var.tag_name}"
  subnets = ["${split(",", var.vpc_zone_subnets)}"]
  security_groups = ["${aws_security_group.redis_sg.id}"]
  internal = true

  listener {
    instance_port     = 6379
    instance_protocol = "tcp"
    lb_port           = 6379
    lb_protocol       = "tcp"
  }

  listener {
    instance_port     = 22121
    instance_protocol = "tcp"
    lb_port           = 22121
    lb_protocol       = "tcp"
  }

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 60
    target              = "TCP:22121"
    interval            = 300
  }
  tags {
    Environment = "${var.environment}"
    Farm_Name = "${var.farm_name}"
    Product = "StormRunner Functional"
    Role = "ES"
  }
}

resource "aws_autoscaling_group" "redis-asg" {
  availability_zones   = ["${split(",", var.availability_zones)}"]
  vpc_zone_identifier  = ["${split(",",var.vpc_zone_subnets)}"]
  name                 = "redis-asg-${var.tag_name}"
  max_size             = "${var.asg_max}"
  min_size             = "${var.asg_min}"
  desired_capacity     = "${var.asg_desired}"
  force_delete         = true
  launch_configuration = "${aws_launch_configuration.redis-lc.name}"
  load_balancers       = ["${aws_elb.redis-elb.name}"]
  health_check_type    = "EC2"
  health_check_grace_period = 300

  tag {
    key                 = "Name"
    value               = "${var.tag_name}"
    propagate_at_launch = "true"
  }
  tag {
    key                 = "SIS_template_tag"
    value               = "redis"
    propagate_at_launch = "true"
  }
  tag {
    key                 = "Owner"
    value               = "SRF_OPS"
    propagate_at_launch = "true"
  }
  tag {
    key                 = "Environment"
    value               = "${var.environment}"
    propagate_at_launch = "true"
  }
  tag {
    key                 = "Farm_Name"
    value               = "${var.farm_name}"
    propagate_at_launch = "true"
  }
  tag {
    key                 = "Product"
    value               = "StormRunner Functional"
    propagate_at_launch = "true"
  }
  tag {
    key                 = "Role"
    value               = "redis"
    propagate_at_launch = "true"
  }
}

resource "aws_launch_configuration" "redis-lc" {
  name          = "redis-lc-${var.tag_name}"
  image_id      = "${lookup(var.aws_amis, var.aws_region)}"
  instance_type = "${var.instance_type}"
  associate_public_ip_address = "${var.associate_public_ip}"

  security_groups = ["${aws_security_group.redis_sg.id}"]
  # user_data       = "${file("userdata.sh")}"
  user_data       = "#!/bin/bash\nset +x\nexport AWS_DEFAULT_REGION=${var.aws_region}\naws s3 cp s3://saas-userdata-scripts/redis_autocluster.py /home/ubuntu/scripts \nsudo service redis-sentinel restart\nsudo python /home/ubuntu/scripts/redis_autocluster.py tag=${var.tag_name}"
  key_name        = "${var.key_name}"
  iam_instance_profile = "EC2Discovery"
}

# Our default security group to access
# the instances over SSH and HTTP
resource "aws_security_group" "redis_sg" {
  name        = "redis_sg-${var.tag_name}"
  description = "Used in the redis"
  vpc_id      = "${var.vpc_id}"

  # SSH access from anywhere
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["${var.operators_cidr}"]
  }
  ingress {
    from_port   = 389
    to_port     = 389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    self = true
  }
  ingress {
    from_port   = 16379
    to_port     = 16379
    protocol    = "tcp"
    self = true
  }
  ingress {
    from_port   = 26379
    to_port     = 26379
    protocol    = "tcp"
    self = true
  }
  ingress {
    from_port   = 22121
    to_port     = 22121
//    security_groups = ["${var.app_sg}"]
    protocol    = "tcp"
    self = true
  }
  ingress {
    from_port = 30
    to_port = 0
    protocol  = "icmp"
//    security_groups = ["${var.app_sg}"]
    cidr_blocks = ["${var.operators_cidr}"]
  }

  # outbound internet access
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

