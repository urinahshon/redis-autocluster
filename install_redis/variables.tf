variable "aws_region" {
  default     = "us-west-2"
  description = "The AWS region to create things in."
}
variable "aws_base_amis" {
  type = "map"
  default = {
    "eu-central-1" = ""
    "us-west-2" = "ami-ba602bc2"
  }
}
variable "key_name" {
  default = "my_key"
  description = "key pair of machines"
}
variable "tag_name" {
  default = "new_redis_image"
  description = "tag name of machines"
}
variable "public_ip_address" {
  default = "false"
  description = "instances should sign to public IPs"
}
variable "subnet_id" {
  default = ""
  description = "instance subnet_id"
}
variable "vpc_id" {
  default = ""
  description = "instance vpc_id"
}
