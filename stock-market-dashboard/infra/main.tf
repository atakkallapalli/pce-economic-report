locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

module "vpc" {
  source = "./modules/vpc"

  name_prefix = local.name_prefix
  vpc_cidr    = var.vpc_cidr
  aws_region  = var.aws_region
}

module "security" {
  source = "./modules/security"

  name_prefix         = local.name_prefix
  vpc_id              = module.vpc.vpc_id
  container_port      = var.container_port
  allowed_cidr_blocks = var.allowed_cidr_blocks
  enable_waf          = var.enable_waf
}

module "alb" {
  source = "./modules/alb"

  name_prefix     = local.name_prefix
  vpc_id          = module.vpc.vpc_id
  public_subnets  = module.vpc.public_subnet_ids
  security_group  = module.security.alb_security_group_id
  container_port  = var.container_port
  certificate_arn = var.certificate_arn
  waf_acl_arn     = module.security.waf_acl_arn
}

module "ecr" {
  source = "./modules/ecr"

  name_prefix = local.name_prefix
}

module "ecs" {
  source = "./modules/ecs"

  name_prefix     = local.name_prefix
  vpc_id          = module.vpc.vpc_id
  private_subnets = module.vpc.private_subnet_ids
  security_group  = module.security.ecs_security_group_id
  target_group_arn = module.alb.target_group_arn
  container_image = "${module.ecr.repository_url}:${var.image_tag}"
  container_port  = var.container_port
  cpu             = var.cpu
  memory          = var.memory
  desired_count   = var.desired_count
  aws_region      = var.aws_region
}
