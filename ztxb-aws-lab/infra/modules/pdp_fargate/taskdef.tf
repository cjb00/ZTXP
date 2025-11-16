resource "aws_iam_role" "pdp_task" {
  name = "${var.project}-pdp-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role" "pdp_exec" {
  name = "${var.project}-pdp-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_ecs_task_definition" "pdp" {
  family                   = "${var.project}-pdp"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"

  execution_role_arn = aws_iam_role.pdp_exec.arn
  task_role_arn      = aws_iam_role.pdp_task.arn

  container_definitions = jsonencode([
    {
      name      = "opa"
      image     = var.image
      essential = true
      portMappings = [
        {
          containerPort = 8181
          hostPort      = 8181
        }
      ]
    }
  ])
}
