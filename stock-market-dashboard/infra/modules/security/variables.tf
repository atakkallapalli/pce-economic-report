variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the ALB"
  type        = list(string)
  default     = []
}

variable "enable_waf" {
  description = "Enable WAF on the ALB"
  type        = bool
  default     = true
}
