import Fastify from 'fastify';

const fastify = Fastify({ logger: true });

fastify.post('/api/mcp/tool', async (request, reply) => {
  const { toolName, args } = request.body;
  // MCP protocol proxy simulation
  return { status: "success", tool: toolName, output: `Executed ${toolName}` };
});

export default async function handler(req, res) {
  await fastify.ready();
  fastify.server.emit('request', req, res);
}
