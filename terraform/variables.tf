variable "aws_region" {
  default     = "us-west-2"
  description = "The AWS region to create things in."
}

# ubuntu-trusty-16.04 with redis
variable "aws_amis" {
  type = "map"
  default = {
    "us-west-2" = "ami-f9917881"
    "eu-central-1" = ""
  }
}

variable "availability_zones" {
  default     = "us-west-2a,us-west-2b"
  description = "List of availability zones"
}

variable "vpc_zone_subnets" {
  default     = "subnet-xxxxxx,subnet-xxxxxx"
  description = "List of availability zones"
}
variable "operators_cidr" {
  type        = "list"
  default     = ["0.0.0.0/0"]
  description = "operators cidr range ips"
}

variable "app_sg" {
  type        = "list"
  default     = [""]
  description = "application security group ID"
}

variable "environment" {
  default = ""
  description = "environment"
}

variable "farm_name" {
  default = ""
  description = "farm name"
}

variable "vpc_id" {
  default = ""
  description = "VPC ID"
}

variable "redis_user" {
  default = "radmin"
  description = "redis user"
}

variable "redis_password" {
  default = "radmin"
  description = "redis password"
}

variable "key_name" {
  default = "SRF"
  description = "key pair of machines"
}

variable "tag_name" {
  default = "redis-terraform"
  description = "tag name of machines"
}

variable "instance_type" {
  default     = "m4.large"
  description = "AWS instance type"
}

variable "asg_min" {
  description = "Min numbers of servers in ASG"
  default     = "3"
}

variable "asg_max" {
  description = "Max numbers of servers in ASG"
  default     = "5"
}
variable "associate_public_ip" {
  description = "associate public ip"
  default     = "false"
}

variable "asg_desired" {
  description = "Desired numbers of servers in ASG"
  default     = "3"
}