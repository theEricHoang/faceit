import * as cdk from 'aws-cdk-lib/core';
import { Template, Match } from 'aws-cdk-lib/assertions';
import { QueuesConstruct } from '../../lib/constructs/queues';

describe('QueuesConstruct', () => {
  test('creates enrollment and attendance queues', () => {
    const app = new cdk.App();
    const stack = new cdk.Stack(app, 'TestStack');

    new QueuesConstruct(stack, 'Queues', {
      queueNamePrefix: 'test',
      visibilityTimeout: cdk.Duration.seconds(300),
      maxReceiveCount: 3,
    });

    const template = Template.fromStack(stack);

    // Assert: 4 queues created (2 main + 2 DLQs)
    template.resourceCountIs('AWS::SQS::Queue', 4);
  });

  test('enrollment queue has DLQ attached', () => {
    const app = new cdk.App();
    const stack = new cdk.Stack(app, 'TestStack');

    new QueuesConstruct(stack, 'Queues', {
      queueNamePrefix: 'test',
      visibilityTimeout: cdk.Duration.seconds(300),
      maxReceiveCount: 3,
    });

    const template = Template.fromStack(stack);

    // Assert: Enrollment queue has redrive policy (DLQ)
    template.hasResourceProperties('AWS::SQS::Queue', {
      QueueName: 'test-enrollment-queue',
      RedrivePolicy: Match.objectLike({
        maxReceiveCount: 3,
      }),
    });
  });

  test('attendance queue has DLQ attached', () => {
    const app = new cdk.App();
    const stack = new cdk.Stack(app, 'TestStack');

    new QueuesConstruct(stack, 'Queues', {
      queueNamePrefix: 'test',
      visibilityTimeout: cdk.Duration.seconds(300),
      maxReceiveCount: 3,
    });

    const template = Template.fromStack(stack);

    // Assert: Attendance queue has redrive policy (DLQ)
    template.hasResourceProperties('AWS::SQS::Queue', {
      QueueName: 'test-attendance-queue',
      RedrivePolicy: Match.objectLike({
        maxReceiveCount: 3,
      }),
    });
  });

  test('queues have correct visibility timeout', () => {
    const app = new cdk.App();
    const stack = new cdk.Stack(app, 'TestStack');

    new QueuesConstruct(stack, 'Queues', {
      queueNamePrefix: 'test',
      visibilityTimeout: cdk.Duration.seconds(300),
      maxReceiveCount: 3,
    });

    const template = Template.fromStack(stack);

    // Assert: Main queues have visibility timeout of 300 seconds
    template.hasResourceProperties('AWS::SQS::Queue', {
      QueueName: 'test-enrollment-queue',
      VisibilityTimeout: 300,
    });
  });

  test('queues are encrypted', () => {
    const app = new cdk.App();
    const stack = new cdk.Stack(app, 'TestStack');

    new QueuesConstruct(stack, 'Queues', {
      queueNamePrefix: 'test',
      visibilityTimeout: cdk.Duration.seconds(300),
      maxReceiveCount: 3,
    });

    const template = Template.fromStack(stack);

    // Assert: All queues have SQS-managed encryption
    template.hasResourceProperties('AWS::SQS::Queue', {
      SqsManagedSseEnabled: true,
    });
  });

  test('DLQs have longer retention period', () => {
    const app = new cdk.App();
    const stack = new cdk.Stack(app, 'TestStack');

    new QueuesConstruct(stack, 'Queues', {
      queueNamePrefix: 'test',
      visibilityTimeout: cdk.Duration.seconds(300),
      maxReceiveCount: 3,
    });

    const template = Template.fromStack(stack);

    // Assert: DLQs have 14-day retention (1209600 seconds)
    template.hasResourceProperties('AWS::SQS::Queue', {
      QueueName: 'test-enrollment-dlq',
      MessageRetentionPeriod: 1209600,
    });
  });
});
