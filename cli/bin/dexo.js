#!/usr/bin/env node

import { program } from 'commander';
import { createInterface } from 'readline';

const API_URL = process.env.DEXO_API_URL || 'http://127.0.0.1:8081';

// Ideally, this should be provided via DEXO_API_KEY environment variable.
const API_KEY = process.env.DEXO_API_KEY || 'default-dev-token';

program
  .name('dexo')
  .description('Dexo CLI client to interact with the LangGraph agent backend.')
  .version('1.0.0');

program
  .command('start')
  .description('Start a conversation with the Dexo agent')
  .requiredOption('-u, --user <prompt>', 'The prompt to send to the agent')
  .action(async (options) => {
    console.log(`
  _____   __   __
 |  __ \\  \\ \\ / /
 | |  | |  \\ V / 
 | |  | |   > <  
 | |__| |  / . \\ 
 |_____/  /_/ \\_\\
    `);
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${API_KEY}`
        },
        body: JSON.stringify({
          message: options.user,
          stream: true
        })
      });

      if (!response.ok) {
        console.error(`Error: Server responded with status ${response.status}`);
        const text = await response.text();
        console.error(text);
        process.exit(1);
      }

      // Stream the response to stdout
      if (response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          // In Server-Sent Events, the payload is prefixed with 'data: '
          // For simplicity in the CLI, we can just print the raw chunks
          // or strip the SSE formatting. Let's print the raw text for now.
          process.stdout.write(chunk);
        }
      } else {
        console.log('No response body received.');
      }
    } catch (error) {
      console.error(`Failed to connect to Dexo API at ${API_URL}`);
      console.error(error.message);
      process.exit(1);
    }
  });

program.parse(process.argv);
