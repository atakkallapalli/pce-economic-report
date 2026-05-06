output "alb_security_group_id" {
  description = "ALB security group ID"
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "ECS security group ID"
  value       = aws_security_group.ecs.id
}

output "waf_acl_arn" {
  description = "WAF ACL ARN (empty string if WAF disabled)"
  value       = var.enable_waf ? aws_wafv2_web_acl.main[0].arn : ""
}
