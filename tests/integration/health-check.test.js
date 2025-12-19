/**
 * Health Check Integration Tests
 */

const { HealthCheckManager, checks } = require('../../src/core/utils/health-check');

describe('HealthCheckManager', () => {
  let healthManager;

  beforeEach(() => {
    healthManager = new HealthCheckManager();
  });

  afterEach(() => {
    healthManager.stopPeriodicChecks();
  });

  describe('registerCheck', () => {
    it('should register a health check', () => {
      healthManager.registerCheck('test', async () => ({ status: 'healthy' }));
      
      expect(healthManager.checks.has('test')).toBe(true);
    });

    it('should register with custom options', () => {
      healthManager.registerCheck('test', async () => ({ status: 'healthy' }), {
        critical: false,
        timeout: 3000
      });
      
      const check = healthManager.checks.get('test');
      expect(check.critical).toBe(false);
      expect(check.timeout).toBe(3000);
    });
  });

  describe('runCheck', () => {
    it('should run a healthy check successfully', async () => {
      healthManager.registerCheck('test', async () => ({ status: 'healthy' }));
      
      const result = await healthManager.runCheck('test');
      
      expect(result.status).toBe('healthy');
      expect(result.latencyMs).toBeDefined();
      expect(result.lastChecked).toBeDefined();
    });

    it('should handle failing checks', async () => {
      healthManager.registerCheck('test', async () => {
        throw new Error('Check failed');
      });
      
      const result = await healthManager.runCheck('test');
      
      expect(result.status).toBe('unhealthy');
      expect(result.message).toBe('Check failed');
    });

    it('should timeout slow checks', async () => {
      healthManager.registerCheck('slow', async () => {
        await global.testUtils.wait(10000);
        return { status: 'healthy' };
      }, { timeout: 100 });
      
      const result = await healthManager.runCheck('slow');
      
      expect(result.status).toBe('unhealthy');
      expect(result.message).toBe('Health check timeout');
    });

    it('should return unhealthy for unknown checks', async () => {
      const result = await healthManager.runCheck('unknown');
      
      expect(result.status).toBe('unhealthy');
      expect(result.message).toBe('Check not found');
    });
  });

  describe('getHealthStatus', () => {
    it('should return healthy when all checks pass', async () => {
      healthManager.registerCheck('check1', async () => ({ status: 'healthy' }));
      healthManager.registerCheck('check2', async () => ({ status: 'healthy' }));
      
      const status = await healthManager.getHealthStatus();
      
      expect(status.status).toBe('healthy');
      expect(status.dependencies).toHaveLength(2);
      expect(status.uptime).toBeDefined();
      expect(status.version).toBeDefined();
    });

    it('should return unhealthy when critical check fails', async () => {
      healthManager.registerCheck('critical', async () => {
        throw new Error('Critical failure');
      }, { critical: true });
      
      healthManager.registerCheck('optional', async () => ({ status: 'healthy' }));
      
      const status = await healthManager.getHealthStatus();
      
      expect(status.status).toBe('unhealthy');
    });

    it('should return degraded when non-critical check fails', async () => {
      healthManager.registerCheck('critical', async () => ({ status: 'healthy' }), { 
        critical: true 
      });
      
      healthManager.registerCheck('optional', async () => {
        throw new Error('Optional failure');
      }, { critical: false });
      
      const status = await healthManager.getHealthStatus();
      
      expect(status.status).toBe('degraded');
    });
  });

  describe('getLivenessStatus', () => {
    it('should always return healthy', () => {
      const status = healthManager.getLivenessStatus();
      
      expect(status.status).toBe('healthy');
      expect(status.timestamp).toBeDefined();
    });
  });

  describe('getReadinessStatus', () => {
    it('should return healthy when critical checks pass', async () => {
      healthManager.registerCheck('critical', async () => ({ status: 'healthy' }), { 
        critical: true 
      });
      
      healthManager.registerCheck('optional', async () => {
        throw new Error('Optional failure');
      }, { critical: false });
      
      const status = await healthManager.getReadinessStatus();
      
      expect(status.status).toBe('healthy');
      // Should only include critical checks
      expect(status.checks).toHaveLength(1);
    });

    it('should return unhealthy when critical check fails', async () => {
      healthManager.registerCheck('critical', async () => {
        throw new Error('Critical failure');
      }, { critical: true });
      
      const status = await healthManager.getReadinessStatus();
      
      expect(status.status).toBe('unhealthy');
    });
  });
});

describe('Memory Health Check', () => {
  it('should return memory usage info', () => {
    const result = checks.checkMemory();
    
    expect(result.status).toBeDefined();
    expect(result.heapUsedMB).toBeDefined();
    expect(result.heapTotalMB).toBeDefined();
    expect(result.percentUsed).toBeDefined();
  });

  it('should have valid memory values', () => {
    const result = checks.checkMemory();
    
    expect(result.heapUsedMB).toBeGreaterThan(0);
    expect(result.heapTotalMB).toBeGreaterThan(0);
    expect(result.percentUsed).toBeGreaterThan(0);
    expect(result.percentUsed).toBeLessThanOrEqual(100);
  });
});

