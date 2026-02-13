import * as cdk from 'aws-cdk-lib/core';
import { Template } from 'aws-cdk-lib/assertions';
import { FaceitDevStack } from '../lib/faceit-dev-stack';

describe('FaceitDevStack', () => {
  test('synthesizes successfully', () => {
    const app = new cdk.App();
    const stack = new FaceitDevStack(app, 'TestStack', {
      env: { account: '123456789012', region: 'us-east-1' },
    });

    const template = Template.fromStack(stack);

    // Assert: Basic resource counts
    template.resourceCountIs('AWS::S3::Bucket', 1);
    template.resourceCountIs('AWS::SQS::Queue', 4); // 2 main + 2 DLQs
    template.resourceCountIs('AWS::IAM::Role', 3); // API, worker task, worker execution
    template.resourceCountIs('AWS::Budgets::Budget', 1);
  });

  test('outputs are defined', () => {
    const app = new cdk.App();
    const stack = new FaceitDevStack(app, 'TestStack', {
      env: { account: '123456789012', region: 'us-east-1' },
    });

    const template = Template.fromStack(stack);

    // Assert: CloudFormation outputs exist
    template.hasOutput('S3BucketName', {});
    template.hasOutput('EnrollmentQueueUrl', {});
    template.hasOutput('AttendanceQueueUrl', {});
    template.hasOutput('ApiRoleArn', {});
    template.hasOutput('WorkerTaskRoleArn', {});
  });
});
