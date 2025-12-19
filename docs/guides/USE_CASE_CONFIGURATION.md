# Use Case Configuration Guide

This guide shows how to configure each bot for different business use cases.

## Table of Contents
1. [Configuration Overview](#configuration-overview)
2. [OpenAI Realtime Bot](#openai-realtime-bot)
3. [ElevenLabs Bridge](#elevenlabs-bridge)
4. [Gemini Bot](#gemini-bot)
5. [OpenAI Pipeline Bot](#openai-pipeline-bot)
6. [Common Use Cases](#common-use-cases)

---

## Configuration Overview

| Bot | Where to Configure | How |
|-----|-------------------|-----|
| **OpenAI Realtime** | Code (`instructions` field) | Edit system prompt |
| **ElevenLabs** | ElevenLabs Dashboard | Create/edit agent |
| **Gemini** | Code (`systemInstruction`) | Edit system prompt |
| **OpenAI Pipeline** | Code (`system` message) | Edit conversation history |

---

## OpenAI Realtime Bot

### Location
`examples/openai-realtime-bot.js` - Line ~139

### Current Configuration
```javascript
session: {
  modalities: ['audio', 'text'],
  instructions: `You are a helpful voice assistant. Keep responses very brief (1-2 sentences max). 
Be conversational and friendly. Respond quickly and naturally.`,
  voice: 'alloy',  // Options: alloy, echo, fable, onyx, nova, shimmer
  // ...
}
```

### How to Customize

```javascript
// Example: Customer Support Bot
instructions: `You are a customer support agent for TechCorp.
Your name is Alex. Be professional but friendly.
Help customers with:
- Product inquiries
- Order status
- Returns and refunds
- Technical support

Always verify the customer's order ID before discussing orders.
If you can't help, offer to transfer to a human agent.
Keep responses brief (2-3 sentences).`
```

### Voice Options
| Voice | Description |
|-------|-------------|
| `alloy` | Neutral, versatile |
| `echo` | Male, warm |
| `fable` | Female, expressive |
| `onyx` | Male, deep |
| `nova` | Female, friendly |
| `shimmer` | Female, soft |

---

## ElevenLabs Bridge

### Location
Configuration is done in the **ElevenLabs Dashboard**, not in code.

### Step 1: Create an Agent
1. Go to [ElevenLabs Conversational AI](https://elevenlabs.io/app/conversational-ai)
2. Click "Create Agent"
3. Configure your agent

### Step 2: Configure Agent Settings

#### System Prompt
```
You are Sarah, a friendly customer service representative for AcmeCorp.

YOUR ROLE:
- Answer product questions
- Help with orders and returns
- Schedule appointments

PERSONALITY:
- Warm and professional
- Patient and helpful
- Clear and concise

RULES:
- Keep responses to 1-2 sentences
- Always confirm understanding
- If unsure, offer to connect to a human
```

#### Dynamic Variables
In your ElevenLabs prompt, use `{{variable_name}}` syntax:

```
Hello {{customer_name}}! I see you're calling about order {{order_id}}.
How can I help you today?
```

These are passed from Exotel via `custom_parameters`:

```javascript
// In Exotel flow, pass custom parameters
// They arrive in the 'start' event and are forwarded to ElevenLabs
```

### Step 3: Get Agent ID
Copy the Agent ID from agent settings and add to `.env`:

```bash
ELEVENLABS_AGENT_ID=agent_xxxxxxxxxxxx
```

---

## Gemini Bot

### Location
`examples/gemini-speech-to-speech-bot.js` - Line ~389

### Current Configuration
```javascript
const model = this.genAI.getGenerativeModel({ 
  model: 'gemini-2.5-flash',
  systemInstruction: 'You are a helpful voice assistant. Keep responses very concise (1-2 sentences max). Be friendly and conversational.'
});
```

### How to Customize

```javascript
// Example: Healthcare Appointment Bot
const model = this.genAI.getGenerativeModel({ 
  model: 'gemini-2.5-flash',
  systemInstruction: `You are Maya, a healthcare appointment assistant for City Medical Center.

CAPABILITIES:
- Schedule, reschedule, and cancel appointments
- Provide clinic hours and locations
- Answer general health questions
- Send appointment reminders

IMPORTANT RULES:
- Never provide medical diagnoses
- Always verify patient name and date of birth
- Confirm all appointment details before booking
- Keep responses brief and clear

TONE:
- Calm and reassuring
- Professional but warm
- Patient with elderly callers`
});
```

### Greeting Configuration
Edit the greeting text in `cacheGreeting()`:

```javascript
async cacheGreeting() {
  const greeting = "Hello! This is Maya from City Medical Center. How may I assist you with your appointment today?";
  // ...
}
```

---

## OpenAI Pipeline Bot

### Location
`examples/speech-to-speech-bot.js` - Line ~475
`examples/simple-conversation-bot.js` - Line ~49

### Current Configuration
```javascript
conversationHistory: [
  {
    role: 'system',
    content: 'You are a helpful voice assistant. Keep responses concise (1-2 sentences), natural, and conversational.'
  }
]
```

### How to Customize

```javascript
// Example: Banking IVR Bot
conversationHistory: [
  {
    role: 'system',
    content: `You are Alex, a virtual assistant for FirstBank.

SERVICES YOU CAN HELP WITH:
1. Account balance inquiries
2. Recent transactions
3. Bill payments
4. Card activation/blocking
5. Branch/ATM locations

SECURITY:
- Always verify: Account number + Last 4 SSN
- Never read full account numbers aloud
- Mask sensitive information

RESPONSES:
- Be brief (1-2 sentences)
- Use natural language, not robotic
- Offer next steps after completing a task
- For complex issues, offer to transfer to human

EXAMPLE:
User: "What's my balance?"
You: "I'd be happy to help with that. For security, could you please confirm the last 4 digits of your SSN?"`
  }
]
```

---

## Common Use Cases

### 1. Customer Support

```javascript
instructions: `You are a customer support agent for [Company].
- Greet customers warmly
- Listen to their issue
- Provide solutions or escalate
- Always confirm resolution
Keep responses to 2-3 sentences.`
```

### 2. Appointment Scheduling

```javascript
instructions: `You are an appointment scheduler for [Business].
- Ask for preferred date and time
- Check availability (simulate)
- Confirm booking details
- Send confirmation message
Keep responses brief and confirm each step.`
```

### 3. Order Status / Tracking

```javascript
instructions: `You are an order status assistant.
- Ask for order number
- Provide shipping status
- Offer solutions for delays
- Handle returns/exchanges
Be helpful and apologetic for any issues.`
```

### 4. Lead Qualification

```javascript
instructions: `You are a sales qualification assistant.
- Introduce the product briefly
- Ask qualifying questions:
  - Budget range
  - Timeline
  - Decision maker
- Schedule demo or transfer to sales
Be enthusiastic but not pushy.`
```

### 5. Survey / Feedback Collection

```javascript
instructions: `You are a customer feedback assistant.
- Thank them for their time
- Ask rating questions (1-5 scale)
- Collect open-ended feedback
- Thank and end call
Keep it brief (under 2 minutes total).`
```

### 6. Technical Support

```javascript
instructions: `You are a tech support assistant.
- Identify the issue
- Walk through troubleshooting steps
- Confirm each step is completed
- Escalate if unresolved after 3 attempts
Be patient and use simple language.`
```

---

## Configuration Files

For more complex configurations, create a config file:

### config/bots/customer-support.js
```javascript
module.exports = {
  name: 'Customer Support Bot',
  voice: 'nova',
  greeting: "Hi! Thanks for calling TechCorp support. I'm here to help.",
  systemPrompt: `You are a customer support agent...`,
  
  // Silence detection tuning
  silenceThreshold: 10,
  minAudioChunks: 40,
  
  // Business hours
  businessHours: {
    start: 9,
    end: 17,
    timezone: 'America/New_York'
  }
};
```

### Using the config:
```javascript
const config = require('../config/bots/customer-support');

// In your bot:
instructions: config.systemPrompt,
voice: config.voice,
```

---

## Environment-Based Configuration

Use different configs for dev/staging/prod:

```javascript
// config/bots/index.js
const env = process.env.NODE_ENV || 'development';

const configs = {
  development: {
    systemPrompt: 'You are a test bot...',
    voice: 'alloy'
  },
  production: {
    systemPrompt: 'You are a professional assistant...',
    voice: 'nova'
  }
};

module.exports = configs[env];
```

---

## Quick Reference

| Use Case | Key Config | Voice Suggestion |
|----------|------------|------------------|
| Customer Support | Professional, helpful | `nova` (friendly) |
| Healthcare | Calm, reassuring | `shimmer` (soft) |
| Banking | Formal, secure | `onyx` (authoritative) |
| Sales | Enthusiastic | `alloy` (versatile) |
| Technical | Patient, clear | `echo` (warm) |

---

## Need Help?

- See [Best Practices](BEST_PRACTICES.md) for optimization tips
- See [Developer Quickstart](DEVELOPER_QUICKSTART.md) to get running
- See [Exotel Integration Issues](EXOTEL_INTEGRATION_ISSUES.md) for troubleshooting

