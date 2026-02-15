###############################################
# IAM: EXECUTION & TASK ROLES
###############################################

resource "aws_iam_role" "pdp_exec" {
  name = "${var.project}-pdp-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "ecs-tasks.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "pdp_exec_ecr" {
  role       = aws_iam_role.pdp_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "pdp_task" {
  name = "${var.project}-pdp-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "ecs-tasks.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

###############################################
# TASK DEFINITION
###############################################

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
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project}-pdp"
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "opa"
          "awslogs-create-group"  = "true"
        }
      }
    }
  ])
}

###############################################
# SECURITY GROUPS
###############################################

resource "aws_security_group" "pdp_alb" {
  name        = "${var.project}-pdp-alb-sg"
  description = "Allow HTTP to PDP ALB from VPC"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP from VPC"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["10.42.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-pdp-alb-sg" }
}

resource "aws_security_group" "pdp_task" {
  name        = "${var.project}-pdp-task-sg"
  description = "Allow OPA traffic from ALB only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "OPA from ALB"
    from_port       = 8181
    to_port         = 8181
    protocol        = "tcp"
    security_groups = [aws_security_group.pdp_alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-pdp-task-sg" }
}
