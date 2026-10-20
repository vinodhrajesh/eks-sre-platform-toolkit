terraform {
  backend "s3" {
    bucket         = "platform-terraform-state-staging"
    key            = "eks-sre-platform-toolkit/staging/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
}
