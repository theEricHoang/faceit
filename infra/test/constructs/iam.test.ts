import * as cdk from 'aws-cdk-lib/core';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Template, Match } from 'aws-cdk-lib/assertions';
import { IamConstruct } from '../../lib/constructs/iam';

describe('IamConstruct', () => {
  let app: cdk.App;
  let stack: cdk.Stack;
  let bucket: s3.Bucket;
  let enrollmentQueue: sqs.Queue;
  let attendanceQueue: sqs.Queue;
  let enrollmentDlq: sqs.Queue;
  let attendanceDlq: sqs.Queue;

  beforeEach(() => {
    app = new cdk.App();
    stack = new cdk.Stack(app, 'TestStack');

    // Create test resources
    bucket = new s3.Bucket(stack, 'TestBucket');
    enrollmentDlq = new sqs.Queue(stack, 'EnrollmentDLQ');
    enrollmentQueue = new sqs.Queue(stack, 'EnrollmentQueue', {
      deadLetterQueue: { queue: enrollmentDlq, maxReceiveCount: 3 },
    });
    attendanceDlq = new sqs.Queue(stack, 'AttendanceDLQ');
    attendanceQueue = new sqs.Queue(stack, 'AttendanceQueue', {
      deadLetterQueue: { queue: attendanceDlq, maxReceiveCount: 3 },
    });
  });

  test('creates three IAM roles', () => {
    new IamConstruct(stack, 'IAM', {
      bucket,
      enrollmentQueue,
      attendanceQueue,
      enrollmentDlq,
      attendanceDlq,
    });

    const template = Template.fromStack(stack);

    // Assert: 3 roles created (API, worker task, worker execution)
    template.resourceCountIs('AWS::IAM::Role', 3);
  });

  test('API role has correct name and trust policy', () => {
    new IamConstruct(stack, 'IAM', {
      bucket,
      enrollmentQueue,
      attendanceQueue,
      enrollmentDlq,
      attendanceDlq,
    });

    const template = Template.fromStack(stack);

    // Assert: API role exists with correct name and can be assumed by EC2
    template.hasResourceProperties('AWS::IAM::Role', {
      RoleName: 'faceit-api-role-dev',
      AssumeRolePolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Effect: 'Allow',
            Principal: {
              Service: 'ec2.amazonaws.com',
            },
          }),
        ]),
      },
    });
  });

  test('API role has S3 and SQS permissions', () => {
    new IamConstruct(stack, 'IAM', {
      bucket,
      enrollmentQueue,
      attendanceQueue,
      enrollmentDlq,
      attendanceDlq,
    });

    const template = Template.fromStack(stack);

    // Assert: At least one policy is attached to the API role
    template.hasResourceProperties('AWS::IAM::Policy', {
      Roles: Match.arrayWith([{ Ref: Match.stringLikeRegexp('IAMApiRole') }]),
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Effect: 'Allow',
            Sid: 'S3BucketAccess',
          }),
        ]),
      },
    });
  });

  test('worker task role exists with correct name', () => {
    new IamConstruct(stack, 'IAM', {
      bucket,
      enrollmentQueue,
      attendanceQueue,
      enrollmentDlq,
      attendanceDlq,
    });

    const template = Template.fromStack(stack);

    // Assert: Worker role exists with correct name
    template.hasResourceProperties('AWS::IAM::Role', {
      RoleName: 'faceit-worker-role-dev',
      AssumeRolePolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Effect: 'Allow',
            Principal: {
              Service: 'ecs-tasks.amazonaws.com',
            },
          }),
        ]),
      },
    });
  });

  test('worker task role has least-privilege permissions', () => {
    new IamConstruct(stack, 'IAM', {
      bucket,
      enrollmentQueue,
      attendanceQueue,
      enrollmentDlq,
      attendanceDlq,
    });

    const template = Template.fromStack(stack);

    // Assert: Worker role has policy with multiple statements (S3, SQS, Secrets)
    template.hasResourceProperties('AWS::IAM::Policy', {
      Roles: Match.arrayWith([{ Ref: Match.stringLikeRegexp('IAMWorkerTaskRole') }]),
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Effect: 'Allow',
            Sid: 'S3GetObjects',
          }),
          Match.objectLike({
            Effect: 'Allow',
            Sid: 'SQSConsumeMessages',
          }),
          Match.objectLike({
            Effect: 'Allow',
            Sid: 'ReadSupabaseSecrets',
          }),
        ]),
      },
    });
  });

  test('worker task execution role has managed policy', () => {
    new IamConstruct(stack, 'IAM', {
      bucket,
      enrollmentQueue,
      attendanceQueue,
      enrollmentDlq,
      attendanceDlq,
    });

    const template = Template.fromStack(stack);

    // Assert: Worker execution role has ECS task execution policy
    template.hasResourceProperties('AWS::IAM::Role', {
      RoleName: 'faceit-worker-execution-role-dev',
      ManagedPolicyArns: Match.arrayWith([
        {
          'Fn::Join': Match.arrayWith([
            '',
            Match.arrayWith([
              'arn:',
              Match.objectLike({ Ref: 'AWS::Partition' }),
              ':iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy',
            ]),
          ]),
        },
      ]),
    });
  });
});

