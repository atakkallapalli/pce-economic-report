variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "fed-rates-corridor"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "container_image" {
  description = "Docker image URI for the Streamlit app"
  type        = string
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8501
}

variable "desired_count" {
  description = "Number of ECS tasks to run"
  type        = number
  default     = 2
}

variable "cpu" {
  description = "CPU units for the ECS task (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "memory" {
  description = "Memory in MiB for the ECS task"
  type        = number
  default     = 1024
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID for LLM reasoning"
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "enable_waf" {
  description = "Enable AWS WAF on the ALB"
  type        = bool
  default     = true
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the ALB (empty = open to internet)"
  type        = list(string)
  default     = []
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS (optional, HTTP-only if empty)"
  type        = string
  default     = ""
}
