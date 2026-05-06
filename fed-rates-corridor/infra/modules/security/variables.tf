variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "container_port" {
  description = "Container port for ECS tasks"
  type        = number
}

variable "allowed_cidr_blocks" {
  description = "Restricted CIDR blocks for ALB access"
  type        = list(string)
  default     = []
}

variable "enable_waf" {
  description = "Enable WAF"
  type        = bool
  default     = true
}
