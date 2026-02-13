import * as cdk from 'aws-cdk-lib/core';
import { Template, Match } from 'aws-cdk-lib/assertions';
import { StorageConstruct } from '../../lib/constructs/storage';

describe('StorageConstruct', () => {
  test('creates S3 bucket with public access blocked', () => {
    const app = new cdk.App();
    const stack = new cdk.Stack(app, 'TestStack');

    new StorageConstruct(stack, 'Storage', {
      bucketName: 'test-bucket',
      lifecycleDays: 1,
    });

    const template = Template.fromStack(stack);

    // Assert: Bucket exists
    template.resourceCountIs('AWS::S3::Bucket', 1);

    // Assert: Public access blocked
    template.hasResourceProperties('AWS::S3::Bucket', {
      PublicAccessBlockConfiguration: {
        BlockPublicAcls: true,
        BlockPublicPolicy: true,
        IgnorePublicAcls: true,
        RestrictPublicBuckets: true,
      },
    });
  });

  test('creates S3 bucket with lifecycle rules', () => {
    const app = new cdk.App();
    const stack = new cdk.Stack(app, 'TestStack');

    new StorageConstruct(stack, 'Storage', {
      bucketName: 'test-bucket',
      lifecycleDays: 1,
    });

    const template = Template.fromStack(stack);

    // Assert: Lifecycle rules exist for both prefixes
    template.hasResourceProperties('AWS::S3::Bucket', {
      LifecycleConfiguration: {
        Rules: Match.arrayWith([
          Match.objectLike({
            Id: 'delete-enrollment-photos',
            Status: 'Enabled',
            ExpirationInDays: 1,
            Prefix: 'enrollment-photos/',
          }),
          Match.objectLike({
            Id: 'delete-class-photos',
            Status: 'Enabled',
            ExpirationInDays: 1,
            Prefix: 'class-photos/',
          }),
        ]),
      },
    });
  });

  test('creates S3 bucket with encryption', () => {
    const app = new cdk.App();
    const stack = new cdk.Stack(app, 'TestStack');

    new StorageConstruct(stack, 'Storage', {
      bucketName: 'test-bucket',
      lifecycleDays: 1,
    });

    const template = Template.fromStack(stack);

    // Assert: S3-managed encryption enabled
    template.hasResourceProperties('AWS::S3::Bucket', {
      BucketEncryption: {
        ServerSideEncryptionConfiguration: [
          {
            ServerSideEncryptionByDefault: {
              SSEAlgorithm: 'AES256',
            },
          },
        ],
      },
    });
  });

  test('creates S3 bucket with CORS configuration', () => {
    const app = new cdk.App();
    const stack = new cdk.Stack(app, 'TestStack');

    new StorageConstruct(stack, 'Storage', {
      bucketName: 'test-bucket',
      lifecycleDays: 1,
    });

    const template = Template.fromStack(stack);

    // Assert: CORS rules exist
    template.hasResourceProperties('AWS::S3::Bucket', {
      CorsConfiguration: {
        CorsRules: Match.arrayWith([
          Match.objectLike({
            AllowedMethods: Match.arrayWith(['PUT', 'POST', 'GET']),
            AllowedOrigins: ['*'],
          }),
        ]),
      },
    });
  });
});
