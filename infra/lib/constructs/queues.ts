import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';

export interface QueuesConstructProps {
  queueNamePrefix: string;
  visibilityTimeout: cdk.Duration;
  maxReceiveCount: number;
}

export class QueuesConstruct extends Construct {
  public readonly enrollmentQueue: sqs.Queue;
  public readonly enrollmentDlq: sqs.Queue;
  public readonly attendanceQueue: sqs.Queue;
  public readonly attendanceDlq: sqs.Queue;

  constructor(scope: Construct, id: string, props: QueuesConstructProps) {
    super(scope, id);

    // ========================================
    // Enrollment Queue + DLQ
    // ========================================

    // Enrollment DLQ
    this.enrollmentDlq = new sqs.Queue(this, 'EnrollmentDLQ', {
      queueName: `${props.queueNamePrefix}-enrollment-dlq`,
      retentionPeriod: cdk.Duration.days(14), // Keep failed messages longer
      encryption: sqs.QueueEncryption.SQS_MANAGED, // Encrypt at rest
    });

    // Enrollment Queue
    this.enrollmentQueue = new sqs.Queue(this, 'EnrollmentQueue', {
      queueName: `${props.queueNamePrefix}-enrollment-queue`,
      visibilityTimeout: props.visibilityTimeout,
      retentionPeriod: cdk.Duration.days(4), // Standard retention
      encryption: sqs.QueueEncryption.SQS_MANAGED,
      deadLetterQueue: {
        queue: this.enrollmentDlq,
        maxReceiveCount: props.maxReceiveCount,
      },
    });

    // ========================================
    // Attendance Queue + DLQ
    // ========================================

    // Attendance DLQ
    this.attendanceDlq = new sqs.Queue(this, 'AttendanceDLQ', {
      queueName: `${props.queueNamePrefix}-attendance-dlq`,
      retentionPeriod: cdk.Duration.days(14),
      encryption: sqs.QueueEncryption.SQS_MANAGED,
    });

    // Attendance Queue
    this.attendanceQueue = new sqs.Queue(this, 'AttendanceQueue', {
      queueName: `${props.queueNamePrefix}-attendance-queue`,
      visibilityTimeout: props.visibilityTimeout,
      retentionPeriod: cdk.Duration.days(4),
      encryption: sqs.QueueEncryption.SQS_MANAGED,
      deadLetterQueue: {
        queue: this.attendanceDlq,
        maxReceiveCount: props.maxReceiveCount,
      },
    });

    // Tags for cost tracking
    cdk.Tags.of(this).add('component', 'queues');
  }
}
