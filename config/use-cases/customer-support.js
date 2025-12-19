/**
 * Customer Support Bot Configuration
 * 
 * Use this template for customer service, helpdesk, support hotlines
 */

module.exports = {
  name: 'Customer Support Bot',
  description: 'Handles customer inquiries, issues, and escalations',
  
  // Voice settings
  voice: 'nova',  // Friendly, professional
  
  // Greeting (pre-cached for instant playback)
  greeting: "Thank you for calling. I'm here to help. How can I assist you today?",
  
  // System prompt / instructions
  systemPrompt: `You are a helpful customer support agent.

YOUR ROLE:
- Listen to customer issues with empathy
- Provide clear solutions or information
- Escalate to human agent when needed

CAPABILITIES:
- Answer product/service questions
- Check order status
- Process returns and refunds
- Troubleshoot common issues
- Schedule callbacks

RULES:
- Be professional but warm
- Keep responses to 2-3 sentences
- Always confirm understanding
- Never argue with customers
- If unsure, offer to transfer to a specialist

ESCALATION TRIGGERS:
- Customer requests human agent
- Issue requires account changes
- Customer is upset after 2 attempts
- Technical issue beyond basic troubleshooting`,

  // Audio settings
  audio: {
    silenceThreshold: 10,     // ~200ms
    minAudioChunks: 40,       // ~800ms minimum speech
    processingCooldown: 800   // ms between processing
  },
  
  // Business hours (optional)
  businessHours: {
    enabled: false,
    timezone: 'America/New_York',
    hours: {
      weekday: { start: 9, end: 18 },
      saturday: { start: 10, end: 14 },
      sunday: null  // Closed
    },
    afterHoursMessage: "We're currently closed. Our hours are Monday-Friday 9am-6pm. Please call back during business hours."
  }
};

