import Fastify from 'fastify';
import { genkit, z } from 'genkit';
import { googleAI } from '@genkit-ai/googleai';

const ai = genkit({
  plugins: [googleAI()],
  model: 'googleai/gemini-1.5-pro',
});

const fastify = Fastify({ logger: true });

fastify.post('/api/genkit', async (request, reply) => {
  const { prompt } = request.body;
  const { text } = await ai.generate(prompt);
  return { result: text };
});

export default async function handler(req, res) {
  await fastify.ready();
  fastify.server.emit('request', req, res);
}
