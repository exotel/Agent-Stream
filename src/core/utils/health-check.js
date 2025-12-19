/**
 * Health Check Utility
 * Enterprise-grade health checks for dependencies and service status
 *
 * Implements:
 * - Kubernetes-style liveness and readiness probes
 * - Dependency health checks (OpenAI, Deepgram, etc.)
 * - Graceful degradation status
 */

const StructuredLogger = require('./structured-logger');
const logger = new StructuredLogger('HEALTH-CHECK');

// ═══════════════════════════════════════════════════════════════════════════════
// Health Check Manager
// ═══════════════════════════════════════════════════════════════════════════════

class HealthCheckManager {
  constructor() {
    this.startTime = Date.now();
    this.checks = new Map();
    this.lastCheckResults = new Map();
    this.checkInterval = null;
    this.version = process.env.npm_package_version || '1.0.0';
  }

  /**
   * Register a health check
   */
  registerCheck(name, checkFn, options = {}) {
    this.checks.set(name, {
      name,
      checkFn,
      critical: options.critical !== false, // Default: critical
      timeout: options.timeout || 5000,
      interval: options.interval || 30000
    });

    logger.info(`Registered health check: ${name}`, {
      critical: options.critical !== false,
      timeout: options.timeout || 5000
    });
  }

  /**
   * Run a single health check with timeout
   */
  async runCheck(name) {
    const check = this.checks.get(name);
    if (!check) {
      return {
        name,
        status: 'unhealthy',
        message: 'Check not found',
        lastChecked: new Date()
      };
    }

    const startTime = Date.now();

    try {
      // Run with timeout
      const result = await Promise.race([
        check.checkFn(),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Health check timeout')), check.timeout)
        )
      ]);

      const checkResult = {
        name,
        status: 'healthy',
        latencyMs: Date.now() - startTime,
        lastChecked: new Date(),
        ...result
      };

      this.lastCheckResults.set(name, checkResult);
      return checkResult;

    } catch (error) {
      const checkResult = {
        name,
        status: 'unhealthy',
        message: error.message,
        latencyMs: Date.now() - startTime,
        lastChecked: new Date()
      };

      this.lastCheckResults.set(name, checkResult);

      logger.warn(`Health check failed: ${name}`, {
        error: error.message,
        latencyMs: checkResult.latencyMs
      });

      return checkResult;
    }
  }

  /**
   * Run all registered health checks
   */
  async runAllChecks() {
    const results = await Promise.all(
      Array.from(this.checks.keys()).map(name => this.runCheck(name))
    );

    return results;
  }

  /**
   * Get overall health status
   */
  async getHealthStatus() {
    const checkResults = await this.runAllChecks();

    // Determine overall status
    let overallStatus = 'healthy';

    for (const result of checkResults) {
      const check = this.checks.get(result.name);

      if (result.status === 'unhealthy') {
        if (check?.critical) {
          overallStatus = 'unhealthy';
          break;
        } else {
          overallStatus = 'degraded';
        }
      }
    }

    return {
      status: overallStatus,
      version: this.version,
      uptime: Math.floor((Date.now() - this.startTime) / 1000),
      timestamp: new Date().toISOString(),
      dependencies: checkResults
    };
  }

  /**
   * Liveness check - is the process alive?
   */
  getLivenessStatus() {
    return {
      status: 'healthy',
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Readiness check - is the service ready to handle requests?
   */
  async getReadinessStatus() {
    // Check critical dependencies only
    const criticalChecks = Array.from(this.checks.entries())
      .filter(([_, check]) => check.critical)
      .map(([name]) => name);

    const results = await Promise.all(
      criticalChecks.map(name => this.runCheck(name))
    );

    const allHealthy = results.every(r => r.status === 'healthy');

    return {
      status: allHealthy ? 'healthy' : 'unhealthy',
      timestamp: new Date().toISOString(),
      checks: results
    };
  }

  /**
   * Start periodic health checks
   */
  startPeriodicChecks(intervalMs = 30000) {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
    }

    this.checkInterval = setInterval(async () => {
      await this.runAllChecks();
    }, intervalMs);

    logger.info(`Started periodic health checks every ${intervalMs}ms`);
  }

  /**
   * Stop periodic health checks
   */
  stopPeriodicChecks() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
      logger.info('Stopped periodic health checks');
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Pre-built Health Checks
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * OpenAI API health check
 */
async function checkOpenAI() {
  if (!process.env.OPENAI_API_KEY) {
    return { status: 'unhealthy', message: 'API key not configured' };
  }

  try {
    const OpenAI = require('openai').default;
    const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

    // Simple API call to verify connectivity
    await openai.models.list({ limit: 1 });

    return { status: 'healthy' };
  } catch (error) {
    return {
      status: 'unhealthy',
      message: error.message
    };
  }
}

/**
 * Deepgram API health check
 */
async function checkDeepgram() {
  if (!process.env.DEEPGRAM_API_KEY) {
    return { status: 'unhealthy', message: 'API key not configured' };
  }

  try {
    const { createClient } = require('@deepgram/sdk');
    const deepgram = createClient(process.env.DEEPGRAM_API_KEY);

    // Get projects to verify connectivity
    await deepgram.manage.getProjects();

    return { status: 'healthy' };
  } catch (error) {
    return {
      status: 'unhealthy',
      message: error.message
    };
  }
}

/**
 * ElevenLabs API health check
 */
async function checkElevenLabs() {
  if (!process.env.ELEVENLABS_API_KEY) {
    return { status: 'unhealthy', message: 'API key not configured' };
  }

  try {
    const response = await fetch('https://api.elevenlabs.io/v1/user', {
      headers: {
        'xi-api-key': process.env.ELEVENLABS_API_KEY
      }
    });

    if (response.ok) {
      return { status: 'healthy' };
    } else {
      return {
        status: 'unhealthy',
        message: `API returned ${response.status}`
      };
    }
  } catch (error) {
    return {
      status: 'unhealthy',
      message: error.message
    };
  }
}

/**
 * Gemini API health check
 */
async function checkGemini() {
  if (!process.env.GEMINI_API_KEY) {
    return { status: 'unhealthy', message: 'API key not configured' };
  }

  try {
    const { GoogleGenerativeAI } = require('@google/generative-ai');
    const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

    // List models to verify connectivity
    const model = genAI.getGenerativeModel({ model: 'gemini-pro' });
    await model.countTokens('test');

    return { status: 'healthy' };
  } catch (error) {
    return {
      status: 'unhealthy',
      message: error.message
    };
  }
}

/**
 * Memory health check
 */
function checkMemory() {
  const used = process.memoryUsage();
  const heapUsedMB = Math.round(used.heapUsed / 1024 / 1024);
  const heapTotalMB = Math.round(used.heapTotal / 1024 / 1024);
  const percentUsed = Math.round((used.heapUsed / used.heapTotal) * 100);

  // Unhealthy if using more than 90% of heap
  const status = percentUsed > 90 ? 'unhealthy' :
    percentUsed > 75 ? 'degraded' : 'healthy';

  return {
    status,
    heapUsedMB,
    heapTotalMB,
    percentUsed
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// Express Routes
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Create health check routes
 */
function createHealthRoutes(healthManager) {
  const express = require('express');
  const router = express.Router();

  // Detailed health status
  router.get('/health', async (req, res) => {
    try {
      const health = await healthManager.getHealthStatus();
      const statusCode = health.status === 'healthy' ? 200 :
        health.status === 'degraded' ? 200 : 503;
      res.status(statusCode).json(health);
    } catch (error) {
      res.status(503).json({
        status: 'unhealthy',
        error: error.message,
        timestamp: new Date().toISOString()
      });
    }
  });

  // Kubernetes liveness probe
  router.get('/health/live', (req, res) => {
    const status = healthManager.getLivenessStatus();
    res.status(200).json(status);
  });

  // Kubernetes readiness probe
  router.get('/health/ready', async (req, res) => {
    try {
      const status = await healthManager.getReadinessStatus();
      const statusCode = status.status === 'healthy' ? 200 : 503;
      res.status(statusCode).json(status);
    } catch (error) {
      res.status(503).json({
        status: 'unhealthy',
        error: error.message,
        timestamp: new Date().toISOString()
      });
    }
  });

  return router;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Exports
// ═══════════════════════════════════════════════════════════════════════════════

module.exports = {
  HealthCheckManager,
  createHealthRoutes,
  checks: {
    checkOpenAI,
    checkDeepgram,
    checkElevenLabs,
    checkGemini,
    checkMemory
  }
};

