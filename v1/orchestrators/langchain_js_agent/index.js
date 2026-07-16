import Fastify from 'fastify';
import { ChatOpenAI } from '@langchain/openai';

const fastify = Fastify({ logger: true });

const chatModel = new ChatOpenAI({
  modelName: 'gpt-4o',
});

fastify.post('/api/langchain-js', async (request, reply) => {
  const { prompt } = request.body;
  const response = await chatModel.invoke(prompt);
  return { result: response.content };
});

export default async function handler(req, res) {
  await fastify.ready();
  fastify.server.emit('request', req, res);
}
