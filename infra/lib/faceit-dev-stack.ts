import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import { StorageConstruct } from './constructs/storage';
import { QueuesConstruct } from './constructs/queues';
import { IamConstruct } from './constructs/iam';
import { BudgetConstruct } from './constructs/budget';

export class FaceitDevStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ========================================
    // 1. Storage: S3 Bucket
    // ========================================
    const storage = new StorageConstruct(this, 'Storage', {
      bucketName: 'faceit-uploads-dev',
      lifecycleDays: 1, // Delete objects after 1 day
    });

    // ========================================
    // 2. Queues: SQS + DLQs
    // ========================================
    const queues = new QueuesConstruct(this, 'Queues', {
      queueNamePrefix: 'faceit',
      visibilityTimeout: cdk.Duration.seconds(300), // 5 minutes
      maxReceiveCount: 3, // Retry 3 times before DLQ
    });

    // ========================================
    // 3. IAM: Roles for API and Worker
    // ========================================
    const iamRoles = new IamConstruct(this, 'IAM', {
      bucket: storage.bucket,
      enrollmentQueue: queues.enrollmentQueue,
      attendanceQueue: queues.attendanceQueue,
      enrollmentDlq: queues.enrollmentDlq,
      attendanceDlq: queues.attendanceDlq,
    });

    // ========================================
    // 4. Budget: Cost Controls
    // ========================================
    new BudgetConstruct(this, 'Budget', {
      budgetName: 'faceit-dev-budget-v2', // Changed name to force recreation with Secrets Manager email
      limitAmount: 5, // $5/month
      alertEmailSecretName: 'faceit/dev/budget-alert-email', // Email stored in Secrets Manager
      thresholds: [50, 80, 100], // Alert at 50%, 80%, 100%
    });

    // ========================================
    // CloudFormation Outputs
    // ========================================

    // S3 Bucket
    new cdk.CfnOutput(this, 'S3BucketName', {
      value: storage.bucket.bucketName,
      description: 'S3 bucket for temporary image uploads',
      exportName: 'FaceitDevS3BucketName',
    });

    new cdk.CfnOutput(this, 'S3BucketArn', {
      value: storage.bucket.bucketArn,
      description: 'S3 bucket ARN',
      exportName: 'FaceitDevS3BucketArn',
    });

    // SQS Queues
    new cdk.CfnOutput(this, 'EnrollmentQueueUrl', {
      value: queues.enrollmentQueue.queueUrl,
      description: 'SQS queue URL for enrollment jobs',
      exportName: 'FaceitDevEnrollmentQueueUrl',
    });

    new cdk.CfnOutput(this, 'EnrollmentQueueArn', {
      value: queues.enrollmentQueue.queueArn,
      description: 'SQS queue ARN for enrollment jobs',
      exportName: 'FaceitDevEnrollmentQueueArn',
    });

    new cdk.CfnOutput(this, 'AttendanceQueueUrl', {
      value: queues.attendanceQueue.queueUrl,
      description: 'SQS queue URL for attendance jobs',
      exportName: 'FaceitDevAttendanceQueueUrl',
    });

    new cdk.CfnOutput(this, 'AttendanceQueueArn', {
      value: queues.attendanceQueue.queueArn,
      description: 'SQS queue ARN for attendance jobs',
      exportName: 'FaceitDevAttendanceQueueArn',
    });

    // IAM Roles
    new cdk.CfnOutput(this, 'ApiRoleArn', {
      value: iamRoles.apiRole.roleArn,
      description: 'IAM role ARN for API (EC2 instance profile)',
      exportName: 'FaceitDevApiRoleArn',
    });

    new cdk.CfnOutput(this, 'WorkerTaskRoleArn', {
      value: iamRoles.workerTaskRole.roleArn,
      description: 'IAM task role ARN for ECS worker',
      exportName: 'FaceitDevWorkerTaskRoleArn',
    });

    new cdk.CfnOutput(this, 'WorkerTaskExecutionRoleArn', {
      value: iamRoles.workerTaskExecutionRole.roleArn,
      description: 'IAM task execution role ARN for ECS worker',
      exportName: 'FaceitDevWorkerTaskExecutionRoleArn',
    });
  }
}
