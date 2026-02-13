import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';

export interface IamConstructProps {
  bucket: s3.IBucket;
  enrollmentQueue: sqs.IQueue;
  attendanceQueue: sqs.IQueue;
  enrollmentDlq: sqs.IQueue;
  attendanceDlq: sqs.IQueue;
}

export class IamConstruct extends Construct {
  public readonly apiRole: iam.Role; // For EC2 instance profile
  public readonly workerTaskExecutionRole: iam.Role;
  public readonly workerTaskRole: iam.Role;

  constructor(scope: Construct, id: string, props: IamConstructProps) {
    super(scope, id);

    // ========================================
    // 1. API Role (EC2 Instance Profile) - Future use
    // ========================================
    this.apiRole = new iam.Role(this, 'ApiRole', {
      roleName: 'faceit-api-role-dev',
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      description: 'Role for FastAPI backend on EC2',
    });

    // S3: Pre-signed URLs and object operations
    this.apiRole.addToPolicy(
      new iam.PolicyStatement({
        sid: 'S3BucketAccess',
        effect: iam.Effect.ALLOW,
        actions: ['s3:PutObject', 's3:GetObject', 's3:DeleteObject'],
        resources: [`${props.bucket.bucketArn}/*`],
      })
    );

    // SQS: Send messages (enqueue jobs)
    this.apiRole.addToPolicy(
      new iam.PolicyStatement({
        sid: 'SQSSendMessages',
        effect: iam.Effect.ALLOW,
        actions: ['sqs:SendMessage', 'sqs:GetQueueUrl', 'sqs:GetQueueAttributes'],
        resources: [props.enrollmentQueue.queueArn, props.attendanceQueue.queueArn],
      })
    );

    // ========================================
    // 2. Worker Task Execution Role (ECS) - Future use
    // ========================================
    this.workerTaskExecutionRole = new iam.Role(this, 'WorkerTaskExecutionRole', {
      roleName: 'faceit-worker-execution-role-dev',
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      description: 'Execution role for ECS worker tasks (pull image, write logs)',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AmazonECSTaskExecutionRolePolicy'
        ),
      ],
    });

    // Allow reading secrets (for Supabase credentials)
    this.workerTaskExecutionRole.addToPolicy(
      new iam.PolicyStatement({
        sid: 'ReadSecrets',
        effect: iam.Effect.ALLOW,
        actions: ['secretsmanager:GetSecretValue'],
        resources: ['arn:aws:secretsmanager:us-east-1:*:secret:faceit/*'],
      })
    );

    // ========================================
    // 3. Worker Task Role (ECS) - Future use
    // ========================================
    this.workerTaskRole = new iam.Role(this, 'WorkerTaskRole', {
      roleName: 'faceit-worker-role-dev',
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      description: 'Task role for ECS worker (access S3, SQS, Secrets)',
    });

    // S3: Download images
    this.workerTaskRole.addToPolicy(
      new iam.PolicyStatement({
        sid: 'S3GetObjects',
        effect: iam.Effect.ALLOW,
        actions: ['s3:GetObject'],
        resources: [`${props.bucket.bucketArn}/*`],
      })
    );

    // SQS: Receive and delete messages
    this.workerTaskRole.addToPolicy(
      new iam.PolicyStatement({
        sid: 'SQSConsumeMessages',
        effect: iam.Effect.ALLOW,
        actions: [
          'sqs:ReceiveMessage',
          'sqs:DeleteMessage',
          'sqs:GetQueueAttributes',
          'sqs:ChangeMessageVisibility', // For extending processing time
        ],
        resources: [props.enrollmentQueue.queueArn, props.attendanceQueue.queueArn],
      })
    );

    // Secrets Manager: Read Supabase credentials
    this.workerTaskRole.addToPolicy(
      new iam.PolicyStatement({
        sid: 'ReadSupabaseSecrets',
        effect: iam.Effect.ALLOW,
        actions: ['secretsmanager:GetSecretValue'],
        resources: ['arn:aws:secretsmanager:us-east-1:*:secret:faceit/*'],
      })
    );

    // Tags
    cdk.Tags.of(this).add('component', 'iam');
  }
}
