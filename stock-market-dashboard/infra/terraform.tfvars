aws_region   = "us-east-1"
environment  = "dev"
project_name = "stock-market-dashboard"

# Container configuration
container_port = 3838
desired_count  = 2
cpu            = 1024
memory         = 2048
image_tag      = "latest"

# Security
enable_waf          = true
allowed_cidr_blocks = []
certificate_arn     = ""
