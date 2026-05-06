package test

import (
	"testing"

	"github.com/gruntwork-io/terratest/modules/terraform"
)

// TestTerraformValidate validates the Terraform configuration
func TestTerraformValidate(t *testing.T) {
	terraformOptions := &terraform.Options{
		TerraformDir: "../",
		Vars: map[string]interface{}{
			"container_image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/fed-rates-corridor:latest",
			"environment":     "dev",
		},
	}

	terraform.InitAndValidate(t, terraformOptions)
}

// TestTerraformModulesValidate validates each module independently
func TestTerraformModulesValidate(t *testing.T) {
	modules := []string{
		"../modules/vpc",
		"../modules/ecs",
		"../modules/alb",
		"../modules/security",
		"../modules/bedrock",
	}

	for _, modulePath := range modules {
		t.Run(modulePath, func(t *testing.T) {
			terraformOptions := &terraform.Options{
				TerraformDir: modulePath,
			}
			terraform.Init(t, terraformOptions)
		})
	}
}
