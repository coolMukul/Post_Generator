import { v4 as uuidv4 } from 'uuid';
import { agentTasksQueue } from '../config/queue.js';
import {
  AgentType,
  ResearchQueryInputSchema,
  InsightExtractionInputSchema,
  LinkedInPostInputSchema,
  ContentWorkflowInputSchema,
  AgentJobResponse,
  ResearchQueryInput,
  InsightExtractionInput,
  LinkedInPostInput,
  ContentWorkflowInput,
} from '../types/schemas.js';

/**
 * Submit an agent job to the queue
 */
export async function submitAgentJob(
  agentType: AgentType,
  input: Record<string, unknown>
): Promise<AgentJobResponse> {
  const jobId = uuidv4();

  // Validate input based on agent type
  let validatedInput: unknown;

  switch (agentType) {
    case AgentType.RESEARCH_QUERY:
      validatedInput = ResearchQueryInputSchema.parse(input);
      break;
    case AgentType.INSIGHT_EXTRACTION:
      validatedInput = InsightExtractionInputSchema.parse(input);
      break;
    case AgentType.LINKEDIN_POST:
      validatedInput = LinkedInPostInputSchema.parse(input);
      break;
    case AgentType.CONTENT_WORKFLOW:
      validatedInput = ContentWorkflowInputSchema.parse(input);
      break;
    default:
      throw new Error(`Unknown agent type: ${agentType}`);
  }

  // Add job to queue
  await agentTasksQueue.add(
    agentType,
    {
      agentType,
      input: validatedInput,
      jobId,
      timestamp: new Date().toISOString()
    },
    {
      jobId,
      removeOnComplete: {
        count: 100,
        age: 24 * 3600
      },
      removeOnFail: {
        count: 500
      }
    }
  );

  console.log(`[Agent:${agentType}] Job submitted: ${jobId}`);

  return {
    success: true,
    jobId,
    agentType,
    message: `Agent job submitted successfully. Poll /queue/jobs/${jobId} for status.`
  };
}

/**
 * Submit Research Query Agent job
 */
export async function submitResearchQueryJob(
  input: ResearchQueryInput
): Promise<AgentJobResponse> {
  return submitAgentJob(AgentType.RESEARCH_QUERY, input);
}

/**
 * Submit Insight Extraction Agent job
 */
export async function submitInsightExtractionJob(
  input: InsightExtractionInput
): Promise<AgentJobResponse> {
  return submitAgentJob(AgentType.INSIGHT_EXTRACTION, input);
}

/**
 * Submit LinkedIn Post Generator Agent job
 */
export async function submitLinkedInPostJob(
  input: LinkedInPostInput
): Promise<AgentJobResponse> {
  return submitAgentJob(AgentType.LINKEDIN_POST, input);
}

/**
 * Submit Content Workflow Agent job (combined Phase 4+5)
 */
export async function submitContentWorkflowJob(
  input: ContentWorkflowInput
): Promise<AgentJobResponse> {
  return submitAgentJob(AgentType.CONTENT_WORKFLOW, input);
}
