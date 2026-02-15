###############################################
# ALB (internal — only reachable from VPC)
###############################################

resource "aws_lb" "pdp" {
  name               = "${var.project}-pdp-alb"
  load_balancer_type = "application"
  internal           = true
  security_groups    = [aws_security_group.pdp_alb.id]
  subnets            = var.public_subnet_ids
}

resource "aws_lb_target_group" "pdp" {
  name     = "${var.project}-pdp-tg"
  port     = 8181
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  # FARGATE + awsvpc → must be "ip"
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/health"
    matcher             = "200"
    interval            = 30
    healthy_threshold   = 3
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "pdp_http" {
  load_balancer_arn = aws_lb.pdp.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.pdp.arn
  }
}

###############################################
# ECS SERVICE
###############################################

resource "aws_ecs_service" "pdp" {
  name            = "${var.project}-pdp-service"
  cluster         = aws_ecs_cluster.this.id
  launch_type     = "FARGATE"
  task_definition = aws_ecs_task_definition.pdp.arn
  desired_count   = 1

  network_configuration {
    assign_public_ip = true
    subnets          = var.public_subnet_ids
    security_groups  = [aws_security_group.pdp_task.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.pdp.arn
    container_name   = "opa"
    container_port   = 8181
  }
}

###############################################
# OUTPUT
###############################################

output "pdp_url" {
  value = aws_lb.pdp.dns_name
}
