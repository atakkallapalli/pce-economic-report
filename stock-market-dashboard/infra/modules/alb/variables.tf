variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnets" {
  description = "List of public subnet IDs for ALB"
  type        = list(string)
}

variable "security_group" {
  description = "Security group ID for the ALB"
  type        = string
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS (empty for HTTP-only)"
  type        = string
  default     = ""
}

variable "waf_acl_arn" {
  description = "WAF Web ACL ARN (empty to skip association)"
  type        = string
  default     = ""
}
