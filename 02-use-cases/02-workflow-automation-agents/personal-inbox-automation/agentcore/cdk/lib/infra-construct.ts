import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda_ from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';
import * as path from 'path';

export interface InfraConstructProps {
  destroyOnDelete?: boolean;
}

export class InfraConstruct extends Construct {
  public readonly lambdaArnMap: Record<string, string>;
  public readonly triggerFn: lambda_.Function;
  public readonly inboxBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: InfraConstructProps = {}) {
    super(scope, id);
    const destroy = props.destroyOnDelete ?? true;
    const removal = destroy ? cdk.RemovalPolicy.DESTROY : cdk.RemovalPolicy.RETAIN;

    // ─── S3 Inbox Bucket
    this.inboxBucket = new s3.Bucket(this, 'InboxBucket', {
      bucketName: cdk.Fn.sub('inbox-agent-${AWS::AccountId}-${AWS::Region}'),
      removalPolicy: removal, autoDeleteObjects: destroy,
      eventBridgeEnabled: true, encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    // ─── DynamoDB Tables
    const tasksTable = new dynamodb.Table(this, 'TasksTable', {
      tableName: 'InboxAgent-Tasks',
      partitionKey: { name: 'task_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: removal, pointInTimeRecovery: true,
    });
    tasksTable.addGlobalSecondaryIndex({
      indexName: 'user-status-index',
      partitionKey: { name: 'user_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    const draftsTable = new dynamodb.Table(this, 'DraftsTable', {
      tableName: 'InboxAgent-Drafts',
      partitionKey: { name: 'draft_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST, removalPolicy: removal,
    });

    const suppressionsTable = new dynamodb.Table(this, 'SuppressionsTable', {
      tableName: 'InboxAgent-Suppressions',
      partitionKey: { name: 'user_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'sender_address', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST, removalPolicy: removal,
    });

    // ─── Lambda Shared Config
    const lambdaDir = path.resolve(__dirname, '..', '..', '..', 'lambdas');
    const runtime = lambda_.Runtime.PYTHON_3_12;
    const defaultEnv = { LOG_LEVEL: 'INFO' };

    // ─── Tool Lambdas
    const getEmailFn = new lambda_.Function(this, 'GetEmailFn', {
      functionName: 'InboxAgent-GetEmail', runtime,
      handler: 'tools.get_email.handler', code: lambda_.Code.fromAsset(lambdaDir),
      timeout: cdk.Duration.seconds(10),
      environment: { ...defaultEnv, INBOX_BUCKET: this.inboxBucket.bucketName },
    });
    this.inboxBucket.grantRead(getEmailFn);

    const saveTaskFn = new lambda_.Function(this, 'SaveTaskFn', {
      functionName: 'InboxAgent-SaveTask', runtime,
      handler: 'tools.save_task.handler', code: lambda_.Code.fromAsset(lambdaDir),
      timeout: cdk.Duration.seconds(10),
      environment: { ...defaultEnv, TASKS_TABLE: tasksTable.tableName },
    });
    tasksTable.grantWriteData(saveTaskFn);

    const listTasksFn = new lambda_.Function(this, 'ListTasksFn', {
      functionName: 'InboxAgent-ListTasks', runtime,
      handler: 'tools.list_tasks.handler', code: lambda_.Code.fromAsset(lambdaDir),
      timeout: cdk.Duration.seconds(10),
      environment: { ...defaultEnv, TASKS_TABLE: tasksTable.tableName },
    });
    tasksTable.grantReadData(listTasksFn);

    const draftReplyFn = new lambda_.Function(this, 'DraftReplyFn', {
      functionName: 'InboxAgent-DraftReply', runtime,
      handler: 'tools.draft_reply.handler', code: lambda_.Code.fromAsset(lambdaDir),
      timeout: cdk.Duration.seconds(30),
      environment: { ...defaultEnv, DRAFTS_TABLE: draftsTable.tableName },
    });
    draftsTable.grantWriteData(draftReplyFn);

    const unsubscribeFn = new lambda_.Function(this, 'UnsubscribeFn', {
      functionName: 'InboxAgent-Unsubscribe', runtime,
      handler: 'tools.unsubscribe.handler', code: lambda_.Code.fromAsset(lambdaDir),
      timeout: cdk.Duration.seconds(10),
      environment: { ...defaultEnv, SUPPRESSIONS_TABLE: suppressionsTable.tableName },
    });
    suppressionsTable.grantWriteData(unsubscribeFn);

    // ─── Trigger Lambda + DLQ
    const dlq = new sqs.Queue(this, 'TriggerDLQ', { queueName: 'InboxAgent-TriggerDLQ', retentionPeriod: cdk.Duration.days(14) });
    this.triggerFn = new lambda_.Function(this, 'TriggerFn', {
      functionName: 'InboxAgent-Trigger', runtime,
      handler: 'trigger.handler.handler', code: lambda_.Code.fromAsset(lambdaDir),
      timeout: cdk.Duration.seconds(60), deadLetterQueue: dlq, retryAttempts: 2,
      environment: { ...defaultEnv, INBOX_BUCKET: this.inboxBucket.bucketName },
    });
    this.inboxBucket.grantRead(this.triggerFn);
    this.triggerFn.addToRolePolicy(new iam.PolicyStatement({ actions: ['bedrock-agentcore:InvokeRuntime'], resources: ['*'] }));

    // ─── EventBridge Rule: S3 → Trigger
    new events.Rule(this, 'InboxUploadRule', {
      ruleName: 'InboxAgent-NewEmail',
      eventPattern: { source: ['aws.s3'], detailType: ['Object Created'], detail: { bucket: { name: [this.inboxBucket.bucketName] }, object: { key: [{ prefix: 'inbox/' }] } } },
      targets: [new targets.LambdaFunction(this.triggerFn)],
    });

    // ─── Lambda ARN Map
    this.lambdaArnMap = {
      'get-email': getEmailFn.functionArn, 'save-task': saveTaskFn.functionArn,
      'list-tasks': listTasksFn.functionArn, 'draft-reply': draftReplyFn.functionArn,
      'unsubscribe': unsubscribeFn.functionArn,
    };

    // ─── Gmail Poller (conditional)
    const gmailSecretsArn = process.env.GMAIL_SECRETS_ARN || '';
    const gmailUserEmail = process.env.GMAIL_USER_EMAIL || 'me';
    const gmailLabelIds = process.env.GMAIL_LABEL_IDS || '';

    if (gmailSecretsArn) {
      const gmailSecret = secretsmanager.Secret.fromSecretCompleteArn(this, 'GmailSecret', gmailSecretsArn);
      const pollerFn = new lambda_.DockerImageFunction(this, 'GmailPollerFn', {
        functionName: 'InboxAgent-GmailPoller',
        code: lambda_.DockerImageCode.fromImageAsset(path.resolve(__dirname, '..', '..', '..', 'lambdas', 'poller')),
        timeout: cdk.Duration.seconds(120), memorySize: 512,
        environment: {
          INBOX_BUCKET: this.inboxBucket.bucketName, GMAIL_SECRETS_ARN: gmailSecretsArn,
          GMAIL_USER_EMAIL: gmailUserEmail, GMAIL_LABEL_IDS: gmailLabelIds,
          MAX_MESSAGES_PER_POLL: process.env.MAX_MESSAGES_PER_POLL || '10',
        },
      });
      this.inboxBucket.grantPut(pollerFn);
      gmailSecret.grantRead(pollerFn);
      gmailSecret.grantRead(draftReplyFn);
      draftReplyFn.addEnvironment('GMAIL_SECRETS_ARN', gmailSecretsArn);

      new events.Rule(this, 'GmailPollSchedule', {
        ruleName: 'InboxAgent-GmailPoll',
        schedule: events.Schedule.rate(cdk.Duration.minutes(5)),
        targets: [new targets.LambdaFunction(pollerFn)],
      });
    }
  }
}
