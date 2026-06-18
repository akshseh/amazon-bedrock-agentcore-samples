import {
  AgentCoreApplication, AgentCoreMcp,
  type AgentCoreProjectSpec, type AgentCoreMcpSpec,
} from '@aws/agentcore-cdk';
import * as cdk from 'aws-cdk-lib';
import { CfnOutput, Stack, type StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { InfraConstruct } from './infra-construct';

export interface AgentCoreStackProps extends StackProps {
  spec: AgentCoreProjectSpec;
  mcpSpec?: AgentCoreMcpSpec;
  credentials?: Record<string, { credentialProviderArn: string }>;
  destroyOnDelete?: boolean;
}

export class AgentCoreStack extends Stack {
  public readonly application: AgentCoreApplication;
  public readonly infra: InfraConstruct;

  constructor(scope: Construct, id: string, props: AgentCoreStackProps) {
    super(scope, id, props);
    const { spec, mcpSpec, credentials, destroyOnDelete } = props;

    // Step 1: Supplementary infrastructure
    this.infra = new InfraConstruct(this, 'Infra', { destroyOnDelete: destroyOnDelete ?? true });

    // Step 2: Patch mcpSpec with real Lambda ARNs
    const patchedMcpSpec = mcpSpec ? this.patchMcpSpecArns(mcpSpec, this.infra.lambdaArnMap) : undefined;

    // Step 3: AgentCore Application
    this.application = new AgentCoreApplication(this, 'Application', { spec });

    // Step 4: AgentCore MCP (Gateway + Targets)
    if (patchedMcpSpec?.agentCoreGateways && patchedMcpSpec.agentCoreGateways.length > 0) {
      new AgentCoreMcp(this, 'Mcp', {
        projectName: spec.name, mcpSpec: patchedMcpSpec,
        agentCoreApplication: this.application, credentials, projectTags: spec.tags,
      });
      // Fix: GatewayTarget DependsOn ordering
      const gatewayRolePolicy = this.node.findAll().find(c =>
        (c as cdk.CfnResource).cfnResourceType === 'AWS::IAM::Policy' &&
        c.node.path.includes('Gateway') && c.node.path.includes('Role') && c.node.path.includes('DefaultPolicy')
      ) as cdk.CfnResource | undefined;
      if (gatewayRolePolicy) {
        this.node.findAll()
          .filter(c => (c as cdk.CfnResource).cfnResourceType === 'AWS::BedrockAgentCore::GatewayTarget')
          .forEach(t => (t as cdk.CfnResource).addDependency(gatewayRolePolicy));
      }
    }

    // Step 5: Inject env vars into Runtime
    const cfnRuntime = this.node.findAll().find(c =>
      (c as cdk.CfnResource).cfnResourceType === 'AWS::BedrockAgentCore::Runtime'
    ) as cdk.CfnResource | undefined;
    if (cfnRuntime) {
      cfnRuntime.addPropertyOverride('EnvironmentVariables.INBOX_BUCKET', this.infra.inboxBucket.bucketName);
      this.infra.triggerFn.addEnvironment('RUNTIME_ARN', cfnRuntime.getAtt('AgentRuntimeArn').toString());
    }

    // Step 6: Outputs
    if (cfnRuntime) {
      new CfnOutput(this, 'RuntimeArn', { value: cfnRuntime.getAtt('AgentRuntimeArn').toString() });
    }
    new CfnOutput(this, 'InboxBucket', { value: this.infra.inboxBucket.bucketName });
  }

  private patchMcpSpecArns(mcpSpec: AgentCoreMcpSpec, lambdaArnMap: Record<string, string>): AgentCoreMcpSpec {
    const patched = JSON.parse(JSON.stringify(mcpSpec));
    for (const gateway of patched.agentCoreGateways ?? []) {
      for (const target of gateway.targets ?? []) {
        if (target.targetType === 'lambdaFunctionArn') {
          const realArn = lambdaArnMap[target.name];
          if (realArn) target.lambdaFunctionArn.lambdaArn = realArn;
        }
      }
    }
    return patched;
  }
}
