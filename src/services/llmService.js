/**
 * Large Language Model Service
 * Unified interface for multiple LLM providers
 */

const Logger = require('../utils/logger');
const aiConfig = require('../../config/ai-services.config');

class LLMService {
  constructor(provider = null) {
    this.provider = provider || aiConfig.llm.provider;
    this.config = aiConfig.llm[this.provider] || aiConfig.llm[`${this.provider}Openai`];
    this.logger = new Logger(`LLM-${this.provider.toUpperCase()}`);
    this.adapter = null;
    this.conversationHistory = [];

    this.initialize();
  }

  /**
   * Initialize LLM adapter based on provider
   */
  initialize() {
    this.logger.info(`Initializing ${this.provider} LLM service...`);

    try {
      switch (this.provider) {
        case 'openai':
          this.adapter = require('./adapters/llm/openaiAdapter');
          break;
        case 'gemini':
          this.adapter = require('./adapters/llm/geminiAdapter');
          break;
        case 'azure':
          this.adapter = require('./adapters/llm/azureOpenaiAdapter');
          break;
        case 'anthropic':
          this.adapter = require('./adapters/llm/anthropicAdapter');
          break;
        case 'groq':
          this.adapter = require('./adapters/llm/groqAdapter');
          break;
        default:
          throw new Error(`Unknown LLM provider: ${this.provider}`);
      }

      this.logger.info(`✓ ${this.provider} LLM initialized`);
    } catch (error) {
      this.logger.error(`Failed to initialize ${this.provider}:`, error.message);
      throw error;
    }
  }

  /**
   * Generate response from user input
   *
   * @param {string} userMessage - User's message
   * @param {Object} context - Optional context
   * @returns {Promise<string>} - AI response
   */
  async generateResponse(userMessage, context = {}) {
    try {
      // Add user message to history
      this.conversationHistory.push({
        role: 'user',
        content: userMessage
      });

      // Generate response
      const response = await this.adapter.generate({
        ...this.config,
        messages: [
          { role: 'system', content: this.config.systemPrompt },
          ...this.conversationHistory
        ],
        context
      });

      // Add assistant response to history
      this.conversationHistory.push({
        role: 'assistant',
        content: response
      });

      // Limit history size
      if (this.conversationHistory.length > aiConfig.general.maxConversationTurns) {
        this.conversationHistory = this.conversationHistory.slice(-aiConfig.general.maxConversationTurns);
      }

      this.logger.debug(`Generated response: "${response.substring(0, 50)}..."`);

      return response;
    } catch (error) {
      this.logger.error('Response generation error:', error.message);
      throw error;
    }
  }

  /**
   * Stream response generation
   *
   * @param {string} userMessage - User's message
   * @param {Function} onChunk - Callback for each chunk
   * @param {Object} context - Optional context
   */
  async *streamResponse(userMessage, context = {}) {
    try {
      // Add user message to history
      this.conversationHistory.push({
        role: 'user',
        content: userMessage
      });

      // Stream response
      const stream = this.adapter.stream({
        ...this.config,
        messages: [
          { role: 'system', content: this.config.systemPrompt },
          ...this.conversationHistory
        ],
        context
      });

      let fullResponse = '';

      for await (const chunk of stream) {
        fullResponse += chunk;
        yield chunk;
      }

      // Add complete response to history
      this.conversationHistory.push({
        role: 'assistant',
        content: fullResponse
      });

    } catch (error) {
      this.logger.error('Stream generation error:', error.message);
      throw error;
    }
  }

  /**
   * Clear conversation history
   */
  clearHistory() {
    this.conversationHistory = [];
    this.logger.debug('Conversation history cleared');
  }

  /**
   * Get conversation history
   */
  getHistory() {
    return this.conversationHistory;
  }

  /**
   * Set system prompt
   */
  setSystemPrompt(prompt) {
    this.config.systemPrompt = prompt;
    this.logger.debug('System prompt updated');
  }

  /**
   * Get provider info
   */
  getInfo() {
    return {
      provider: this.provider,
      model: this.config.model,
      historyLength: this.conversationHistory.length
    };
  }
}

module.exports = LLMService;

