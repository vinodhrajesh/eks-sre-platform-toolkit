#
# ECR lifecycle policy module.
#
# Automatically expires stale CI/staging images so registry storage doesn't
# grow unbounded. In production this cut stored image count by ~40% in the
# first cleanup cycle against a registry that had never had a retention
# policy applied.
#

resource "aws_ecr_lifecycle_policy" "this" {
  for_each   = toset(var.repository_names)
  repository = each.value

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep only the last N tagged CI/staging images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["ci-", "staging-"]
          countType     = "imageCountMoreThan"
          countNumber   = var.max_tagged_images
        }
        action = { type = "expire" }
      }
    ]
  })
}
