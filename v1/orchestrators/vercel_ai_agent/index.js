import Fastify from 'fastify';
import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';

const fastify = Fastify({ logger: true });

fastify.post('/api/orchestrate', async (request, reply) => {
  const { prompt } = request.body;
  
  // Example AI SDK call
  const { text } = await generateText({
    model: openai('gpt-4o'),
    prompt: prompt,
  });

  return { result: text };
});

export default async function handler(req, res) {
  await fastify.ready();
  fastify.server.emit('request', req, res);
}
