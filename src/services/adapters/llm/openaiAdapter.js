/**
 * OpenAI LLM Adapter
 * Install: npm install openai
 */

const Logger = require('../../../utils/logger');
const logger = new Logger('OPENAI');

let OpenAI;
try {
  OpenAI = require('openai').default;
} catch (error) {
  logger.warn('OpenAI SDK not installed. Install with: npm install openai');
}

class OpenAIAdapter {
  /**
   * Generate response
   */
  static async generate(config) {
    if (!OpenAI) {
      throw new Error('OpenAI SDK not installed');
    }

    try {
      const openai = new OpenAI({
        apiKey: config.apiKey
      });

      const response = await openai.chat.completions.create({
        model: config.model,
        messages: config.messages,
        temperature: config.temperature,
        max_tokens: config.maxTokens
      });

      return response.choices[0].message.content;
    } catch (error) {
      logger.error('OpenAI generation error:', error.message);
      throw error;
    }
  }

  /**
   * Stream response
   */
  static async *stream(config) {
    if (!OpenAI) {
      throw new Error('OpenAI SDK not installed');
    }

    try {
      const openai = new OpenAI({
        apiKey: config.apiKey
      });

      const stream = await openai.chat.completions.create({
        model: config.model,
        messages: config.messages,
        temperature: config.temperature,
        max_tokens: config.maxTokens,
        stream: true
      });

      for await (const chunk of stream) {
        const content = chunk.choices[0]?.delta?.content || '';
        if (content) {
          yield content;
        }
      }
    } catch (error) {
      logger.error('OpenAI stream error:', error.message);
      throw error;
    }
  }
}

module.exports = OpenAIAdapter;

