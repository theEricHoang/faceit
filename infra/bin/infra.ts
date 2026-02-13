#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { FaceitDevStack } from '../lib/faceit-dev-stack';

const app = new cdk.App();

new FaceitDevStack(app, 'FaceitDevStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: 'us-east-1',
  },
  stackName: 'faceit-dev',
  description: 'FaceIT Development Environment - Minimal AWS resources for async face recognition',
  tags: {
    project: 'faceit',
    environment: 'dev',
    'cost-center': 'school-project',
  },
});

app.synth();
