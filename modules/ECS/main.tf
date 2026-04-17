# --- ECS Cluster ---
resource "aws_ecs_cluster" "cluster" {
  name = "translation-api-cluster"
}

# --- Security Group for ALB & ECS ---
resource "aws_security_group" "ecs_sg" {
  name        = "ecs-sg"
  description = "Allow HTTP inbound"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- Application Load Balancer ---
resource "aws_lb" "alb" {
  name               = "translation-api-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.ecs_sg.id]
  subnets            = var.subnets
}

resource "aws_lb_target_group" "tg" {
  name     = "translation-api-tg"
  port     = var.container_port
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  target_type = "ip"
}

resource "aws_lb_listener" "listener" {
  load_balancer_arn = aws_lb.alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tg.arn
  }
}

# --- ECS Task Definition ---
resource "aws_ecs_task_definition" "task" {
  family                   = "translation-api-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            =  var.task_role_arn
  depends_on = [aws_cloudwatch_log_group.ecs_logs]
 container_definitions = jsonencode([
  {
    name      = "translation-api"
    image     = var.image_url
    essential = true

    portMappings = [
      {
        containerPort = var.container_port
        hostPort      = var.container_port
      }
    ]

    environment = [
      {
        name  = "TRANSLATION_API_URL"
        value = var.translation_api_url != "" ? var.translation_api_url : "http://${aws_lb.alb.dns_name}/translate"
      },
      {
        name  = "AWS_REGION"
        value = var.aws_region
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = "/ecs/translation-api-task"
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "ecs"
      }
    }
  }
])
}

# --- ECS Service ---
resource "aws_ecs_service" "service" {
  name            = "translation-api-service"
  cluster         = aws_ecs_cluster.cluster.id
  task_definition = aws_ecs_task_definition.task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnets
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.tg.arn
    container_name   = "translation-api"
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener.listener]
}
resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/translation-api-task"
  retention_in_days = 7
}