#!/usr/bin/env node
import { AgentCoreStack } from '../lib/cdk-stack';
import { ConfigIO, type AwsDeploymentTarget } from '@aws/agentcore-cdk';
import { App, type Environment } from 'aws-cdk-lib';
import * as path from 'path';
import * as fs from 'fs';

function toEnvironment(target: AwsDeploymentTarget): Environment {
  return { account: target.account, region: target.region };
}

function toStackName(projectName: string, targetName: string): string {
  return `AgentCore-${projectName}-${targetName}`;
}

async function main() {
  const configRoot = path.resolve(process.cwd(), '..');
  const configIO = new ConfigIO({ baseDir: configRoot });
  const spec = await configIO.readProjectSpec();
  const targets = await configIO.readAWSDeploymentTargets();

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const specAny = spec as any;
  const mcpSpec = specAny.agentCoreGateways?.length
    ? { agentCoreGateways: specAny.agentCoreGateways, mcpRuntimeTools: specAny.mcpRuntimeTools, unassignedTargets: specAny.unassignedTargets }
    : undefined;

  let deployedState: Record<string, unknown> | undefined;
  try { deployedState = JSON.parse(fs.readFileSync(path.join(configRoot, '.cli', 'deployed-state.json'), 'utf8')); } catch { /* first deploy */ }

  if (targets.length === 0) throw new Error('No targets in agentcore/aws-targets.json');

  const app = new App();
  for (const target of targets) {
    const env = toEnvironment(target);
    const stackName = toStackName(spec.name, target.name);
    const targetState = (deployedState as Record<string, unknown>)?.targets as Record<string, Record<string, unknown>> | undefined;
    const targetResources = targetState?.[target.name]?.resources as Record<string, unknown> | undefined;
    const credentials = targetResources?.credentials as Record<string, { credentialProviderArn: string }> | undefined;

    new AgentCoreStack(app, stackName, {
      spec, mcpSpec, credentials,
      destroyOnDelete: (process.env.DESTROY_ON_DELETE ?? 'true').toLowerCase() === 'true',
      env,
      description: `AgentCore Inbox Agent deployed to ${target.name} (${target.region})`,
      tags: { 'agentcore:project-name': spec.name, 'agentcore:target-name': target.name },
    });
  }
  app.synth();
}

main().catch((error: unknown) => { console.error('CDK synthesis failed:', error instanceof Error ? error.message : error); process.exitCode = 1; });
