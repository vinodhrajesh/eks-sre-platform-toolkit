terraform {
  backend "s3" {
    bucket         = "platform-terraform-state-production"
    key            = "eks-sre-platform-toolkit/production/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
}
