variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}
