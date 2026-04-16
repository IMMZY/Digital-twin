terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Read the current AWS account information.
# data.aws_caller_identity.current.account_id gives your 12-digit account ID.
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local values: computed once and reused across all .tf files.
# name_prefix combines the project name and the current workspace name,
# ensuring every resource is uniquely named per environment.
locals {
  name_prefix  = "${var.project_name}-${terraform.workspace}"
  s3_origin_id = "${var.project_name}-s3-origin-${terraform.workspace}"
}
