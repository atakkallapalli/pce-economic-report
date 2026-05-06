variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnets" {
  description = "Public subnet IDs for ALB"
  type        = list(string)
}

variable "security_group" {
  description = "Security group ID for ALB"
  type        = string
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS"
  type        = string
  default     = ""
}

variable "waf_acl_arn" {
  description = "WAF ACL ARN to associate"
  type        = string
  default     = ""
}
