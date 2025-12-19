#!/usr/bin/env node

/**
 * Bot Integration Test Script
 * Tests all bots by starting them and verifying basic functionality
 */

const WebSocket = require('ws');
const http = require('http');
const { spawn } = require('child_process');
const path = require('path');

const BOTS = [
  {
    name: 'Simple Conversation Bot',
    script: 'examples/simple-conversation-bot.js',
    description: 'GPT-4 based conversation bot'
  },
  {
    name: 'Speech-to-Speech Bot',
    script: 'examples/speech-to-speech-bot.js',
    description: 'GPT-4 with noise cancellation'
  },
  {
    name: 'Gemini Bot',
    script: 'examples/gemini-speech-to-speech-bot.js',
    description: 'Google Gemini 2.0 Flash'
  },
  {
    name: 'ElevenLabs Bridge',
    script: 'examples/elevenlabs-bridge.js',
    description: 'ElevenLabs Conversational AI'
  }
];

const PORT = 5001;
const STARTUP_WAIT = 3000;
const TEST_TIMEOUT = 10000;

// Colors for console
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Check if port is in use
 */
async function isPortInUse(port) {
  return new Promise((resolve) => {
    const req = http.get(`http://localhost:${port}/health`, (res) => {
      resolve(true);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(1000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

/**
 * Kill any process on port
 */
async function killProcessOnPort(port) {
  return new Promise((resolve) => {
    const kill = spawn('lsof', ['-ti', `:${port}`]);
    let pids = '';
    
    kill.stdout.on('data', (data) => {
      pids += data.toString();
    });
    
    kill.on('close', () => {
      if (pids.trim()) {
        const killPids = spawn('kill', ['-9', ...pids.trim().split('\n')]);
        killPids.on('close', () => {
          setTimeout(resolve, 1000);
        });
      } else {
        resolve();
      }
    });
  });
}

/**
 * Start a bot and return the process
 */
function startBot(scriptPath) {
  const fullPath = path.join(__dirname, '..', scriptPath);
  const proc = spawn('node', [fullPath], {
    cwd: path.join(__dirname, '..'),
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, LOG_LEVEL: 'error' }
  });
  
  // Capture output for debugging
  let output = '';
  proc.stdout.on('data', (data) => {
    output += data.toString();
  });
  proc.stderr.on('data', (data) => {
    output += data.toString();
  });
  
  proc.output = () => output;
  
  return proc;
}

/**
 * Test health endpoint
 */
async function testHealth() {
  return new Promise((resolve, reject) => {
    const req = http.get(`http://localhost:${PORT}/health`, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          resolve({
            success: res.statusCode === 200,
            status: json.status,
            uptime: json.uptime,
            connections: json.connections
          });
        } catch (e) {
          reject(new Error('Invalid JSON response'));
        }
      });
    });
    
    req.on('error', reject);
    req.setTimeout(5000, () => {
      req.destroy();
      reject(new Error('Health check timeout'));
    });
  });
}

/**
 * Test WebSocket connection
 */
async function testWebSocket() {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(`ws://localhost:${PORT}/media`);
    const timeout = setTimeout(() => {
      ws.close();
      reject(new Error('WebSocket connection timeout'));
    }, 5000);
    
    ws.on('open', () => {
      clearTimeout(timeout);
      
      // Send a mock start event
      const startEvent = {
        event: 'start',
        sequence_number: '1',
        start: {
          call_sid: 'test-call-123',
          account_sid: 'test-account',
          from: '+1234567890',
          to: '+0987654321',
          media_format: {
            encoding: 'linear16',
            sample_rate: 8000,
            bit_rate: 16
          }
        }
      };
      
      ws.send(JSON.stringify(startEvent));
      
      // Wait a bit then close
      setTimeout(() => {
        ws.close();
        resolve({ success: true, connected: true });
      }, 1000);
    });
    
    ws.on('error', (err) => {
      clearTimeout(timeout);
      reject(err);
    });
  });
}

/**
 * Test a single bot
 */
async function testBot(bot, index) {
  log(`\n${'═'.repeat(60)}`, 'blue');
  log(`Testing ${index + 1}/${BOTS.length}: ${bot.name}`, 'cyan');
  log(`Description: ${bot.description}`, 'cyan');
  log('═'.repeat(60), 'blue');
  
  const results = {
    name: bot.name,
    script: bot.script,
    startup: false,
    health: false,
    websocket: false,
    error: null
  };
  
  let proc = null;
  
  try {
    // Start the bot
    log('  → Starting bot...', 'yellow');
    proc = startBot(bot.script);
    
    // Wait for startup
    await sleep(STARTUP_WAIT);
    
    // Check if process is still running
    if (proc.exitCode !== null) {
      throw new Error(`Bot exited with code ${proc.exitCode}\n${proc.output()}`);
    }
    
    results.startup = true;
    log('  ✓ Bot started successfully', 'green');
    
    // Test health endpoint
    log('  → Testing health endpoint...', 'yellow');
    const health = await testHealth();
    results.health = health.success;
    log(`  ✓ Health check passed (status: ${health.status})`, 'green');
    
    // Test WebSocket connection
    log('  → Testing WebSocket connection...', 'yellow');
    const wsResult = await testWebSocket();
    results.websocket = wsResult.success;
    log('  ✓ WebSocket connection successful', 'green');
    
  } catch (error) {
    results.error = error.message;
    log(`  ✗ Error: ${error.message}`, 'red');
  } finally {
    // Stop the bot
    if (proc && proc.exitCode === null) {
      log('  → Stopping bot...', 'yellow');
      proc.kill('SIGTERM');
      await sleep(1000);
      
      // Force kill if still running
      if (proc.exitCode === null) {
        proc.kill('SIGKILL');
      }
    }
  }
  
  return results;
}

/**
 * Print summary
 */
function printSummary(results) {
  log('\n' + '═'.repeat(60), 'blue');
  log('TEST SUMMARY', 'cyan');
  log('═'.repeat(60), 'blue');
  
  let passed = 0;
  let failed = 0;
  
  results.forEach((result, index) => {
    const allPassed = result.startup && result.health && result.websocket;
    const status = allPassed ? '✓ PASS' : '✗ FAIL';
    const color = allPassed ? 'green' : 'red';
    
    log(`\n${index + 1}. ${result.name}`, color);
    log(`   Script: ${result.script}`);
    log(`   Startup:   ${result.startup ? '✓' : '✗'}`);
    log(`   Health:    ${result.health ? '✓' : '✗'}`);
    log(`   WebSocket: ${result.websocket ? '✓' : '✗'}`);
    
    if (result.error) {
      log(`   Error: ${result.error}`, 'red');
    }
    
    if (allPassed) passed++;
    else failed++;
  });
  
  log('\n' + '═'.repeat(60), 'blue');
  log(`RESULTS: ${passed} passed, ${failed} failed`, passed === results.length ? 'green' : 'yellow');
  log('═'.repeat(60), 'blue');
  
  return failed === 0;
}

/**
 * Main test runner
 */
async function main() {
  log('\n🤖 EXOTEL VOICE BOT - INTEGRATION TEST SUITE\n', 'cyan');
  
  // Check for required environment
  if (!process.env.OPENAI_API_KEY) {
    log('⚠️  Warning: OPENAI_API_KEY not set. Some bots may fail.\n', 'yellow');
  }
  
  // Kill any existing process on port
  log('Cleaning up port 5001...', 'yellow');
  await killProcessOnPort(PORT);
  
  const results = [];
  
  for (let i = 0; i < BOTS.length; i++) {
    // Clean up between tests
    await killProcessOnPort(PORT);
    await sleep(500);
    
    const result = await testBot(BOTS[i], i);
    results.push(result);
  }
  
  const success = printSummary(results);
  
  // Final cleanup
  await killProcessOnPort(PORT);
  
  process.exit(success ? 0 : 1);
}

// Run tests
main().catch((error) => {
  log(`\n✗ Test runner error: ${error.message}`, 'red');
  process.exit(1);
});

