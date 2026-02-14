import * as budgets from 'aws-cdk-lib/aws-budgets';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';

export interface BudgetConstructProps {
  budgetName: string;
  limitAmount: number;
  alertEmailSecretName?: string; // Optional: name of Secrets Manager secret containing email
  thresholds: number[]; // e.g., [50, 80, 100]
}

export class BudgetConstruct extends Construct {
  constructor(scope: Construct, id: string, props: BudgetConstructProps) {
    super(scope, id);

    // Look up the email from Secrets Manager if secret name provided
    let alertEmail: string | undefined;
    if (props.alertEmailSecretName) {
      const secret = secretsmanager.Secret.fromSecretNameV2(
        this,
        'BudgetEmailSecret',
        props.alertEmailSecretName
      );
      // Use secret value as JSON and extract the "email" field
      alertEmail = secret.secretValueFromJson('email').unsafeUnwrap();
    }

    // Create notification configs for each threshold
    const notificationsWithSubscribers: budgets.CfnBudget.NotificationWithSubscribersProperty[] =
      props.thresholds.map((threshold) => {
        const notification: budgets.CfnBudget.NotificationProperty = {
          notificationType: 'ACTUAL',
          comparisonOperator: 'GREATER_THAN',
          threshold: threshold,
          thresholdType: 'PERCENTAGE',
        };

        // If email was retrieved from Secrets Manager, use it
        const subscribers: budgets.CfnBudget.SubscriberProperty[] = alertEmail
          ? [
              {
                subscriptionType: 'EMAIL',
                address: alertEmail,
              },
            ]
          : [
              {
                subscriptionType: 'EMAIL',
                address: 'noreply@example.com', // Fallback - won't be used if secret is provided
              },
            ];

        return {
          notification,
          subscribers,
        };
      });

    new budgets.CfnBudget(this, 'MonthlyBudget', {
      budget: {
        budgetName: props.budgetName,
        budgetType: 'COST',
        timeUnit: 'MONTHLY',
        budgetLimit: {
          amount: props.limitAmount,
          unit: 'USD',
        },
        costFilters: {
          // Optional: Filter by project tag
          TagKeyValue: ['user:project$faceit'],
        },
      },
      notificationsWithSubscribers,
    });
  }
}
