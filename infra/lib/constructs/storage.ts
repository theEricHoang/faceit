import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';

export interface StorageConstructProps {
  bucketName: string;
  lifecycleDays: number;
}

export class StorageConstruct extends Construct {
  public readonly bucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: StorageConstructProps) {
    super(scope, id);

    this.bucket = new s3.Bucket(this, 'UploadsBucket', {
      bucketName: props.bucketName,

      // Security: Block all public access
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,

      // Encryption: Server-side encryption with S3-managed keys
      encryption: s3.BucketEncryption.S3_MANAGED,

      // Lifecycle: Delete objects after N days
      lifecycleRules: [
        {
          id: 'delete-enrollment-photos',
          prefix: 'enrollment-photos/',
          expiration: cdk.Duration.days(props.lifecycleDays),
          enabled: true,
        },
        {
          id: 'delete-class-photos',
          prefix: 'class-photos/',
          expiration: cdk.Duration.days(props.lifecycleDays),
          enabled: true,
        },
      ],

      // Versioning: Disabled (not needed for temp files)
      versioned: false,

      // Deletion: RETAIN to prevent accidental data loss
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      autoDeleteObjects: false, // Don't auto-delete on stack destruction

      // CORS: Allow frontend to upload directly via pre-signed URLs
      cors: [
        {
          allowedMethods: [
            s3.HttpMethods.PUT,
            s3.HttpMethods.POST,
            s3.HttpMethods.GET,
          ],
          allowedOrigins: ['*'], // Tighten in production
          allowedHeaders: ['*'],
          maxAge: 3000,
        },
      ],
    });

    // Tags for cost tracking
    cdk.Tags.of(this.bucket).add('component', 'storage');
  }
}
