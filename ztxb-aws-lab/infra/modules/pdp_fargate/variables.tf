variable "project" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "security_group_ids" {
  type = list(string)
}

variable "image" {
  type = string
}

variable "region" {
  type = string
}

variable "default_sg_id" {
  type = string
}
