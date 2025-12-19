/**
 * Exotel Voice Bot - Type Definitions
 * Enterprise-grade type definitions for the voice bot framework
 */

// ═══════════════════════════════════════════════════════════════════════════════
// Exotel WebSocket Events
// ═══════════════════════════════════════════════════════════════════════════════

export interface ExotelMediaFormat {
  encoding: 'audio/x-mulaw' | 'audio/x-alaw' | 'linear16';
  sample_rate: number;
  bit_rate: number;
}

export interface ExotelCustomParameters {
  [key: string]: string;
}

export interface ExotelStreamInfo {
  call_sid: string;
  account_sid: string;
  from: string;
  to: string;
  media_format: ExotelMediaFormat;
  custom_parameters?: ExotelCustomParameters;
}

export interface ExotelConnectedEvent {
  event: 'connected';
  protocol: string;
  version: string;
}

export interface ExotelStartEvent {
  event: 'start';
  sequence_number: string;
  start: ExotelStreamInfo;
}

export interface ExotelMediaEvent {
  event: 'media';
  sequence_number: string;
  media: {
    chunk: string;
    timestamp: string;
    payload: string; // base64 encoded audio
  };
}

export interface ExotelDTMFEvent {
  event: 'dtmf';
  sequence_number: string;
  dtmf: {
    digit: string;
    duration: string;
  };
}

export interface ExotelStopEvent {
  event: 'stop';
  sequence_number: string;
  stop: {
    call_sid: string;
    account_sid: string;
    reason: string;
  };
}

export interface ExotelMarkEvent {
  event: 'mark';
  sequence_number: string;
  mark: {
    name: string;
  };
}

export type ExotelIncomingEvent =
  | ExotelConnectedEvent
  | ExotelStartEvent
  | ExotelMediaEvent
  | ExotelDTMFEvent
  | ExotelStopEvent
  | ExotelMarkEvent;

// ═══════════════════════════════════════════════════════════════════════════════
// Outgoing Events (Bot → Exotel)
// ═══════════════════════════════════════════════════════════════════════════════

export interface ExotelOutgoingMediaEvent {
  event: 'media';
  sequence_number: string;
  stream_sid: string;
  media: {
    chunk: string;
    timestamp: string;
    payload: string;
  };
}

export interface ExotelOutgoingMarkEvent {
  event: 'mark';
  sequence_number: string;
  stream_sid: string;
  mark: {
    name: string;
  };
}

export interface ExotelOutgoingClearEvent {
  event: 'clear';
  stream_sid: string;
}

export type ExotelOutgoingEvent =
  | ExotelOutgoingMediaEvent
  | ExotelOutgoingMarkEvent
  | ExotelOutgoingClearEvent;

// ═══════════════════════════════════════════════════════════════════════════════
// Processed Data Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface MediaData {
  chunk: number;
  timestamp: number;
  audioBuffer: Buffer;
  duration: number;
  sequenceNumber: string;
}

export interface DTMFData {
  digit: string;
  duration: number;
  sequenceNumber: string;
}

export interface StopData {
  callSid: string;
  accountSid: string;
  reason: string;
  totalChunks: number;
  duration: number;
}

export interface MarkData {
  name: string;
  sequenceNumber: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Bot Callbacks
// ═══════════════════════════════════════════════════════════════════════════════

export interface BotCallbacks {
  onStart?: (streamInfo: ExotelStreamInfo) => void | Promise<void>;
  onMedia?: (mediaData: MediaData) => void | Promise<void>;
  onDTMF?: (dtmfData: DTMFData) => void | Promise<void>;
  onStop?: (stopData: StopData) => void | Promise<void>;
  onMark?: (markData: MarkData) => void | Promise<void>;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Configuration Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface ServerConfig {
  port: number;
  host: string;
  wsPath: string;
}

export interface SSLConfig {
  enabled: boolean;
  certPath?: string;
  keyPath?: string;
}

export interface AuthConfig {
  enabled: boolean;
  apiKey?: string;
  apiToken?: string;
}

export interface LoggingConfig {
  level: 'error' | 'warn' | 'info' | 'debug';
  logMediaPayloads: boolean;
  logEventsToFile: boolean;
  logHttpRequests: boolean;
  jsonFormat: boolean;
}

export interface AudioConfig {
  defaultSampleRate: number;
  supportedSampleRates: number[];
}

export interface ChunkSizeConfig {
  min: number;
  max: number;
  alignment: number;
}

export interface NoiseCancellationConfig {
  enabled: boolean;
  processorType: 'rnnoise' | 'spectral';
  mode: 'both' | 'incoming_only' | 'outgoing_only' | 'disabled';
  maxLatencyMs: number;
  enableStats: boolean;
}

export interface AppConfig {
  server: ServerConfig;
  ssl: SSLConfig;
  auth: AuthConfig;
  logging: LoggingConfig;
  audio: AudioConfig;
  chunkSize: ChunkSizeConfig;
  noiseCancellation: NoiseCancellationConfig;
}

// ═══════════════════════════════════════════════════════════════════════════════
// AI Service Types
// ═══════════════════════════════════════════════════════════════════════════════

export type STTProvider = 'whisper' | 'deepgram' | 'google' | 'azure' | 'assemblyai';
export type TTSProvider = 'openai' | 'elevenlabs' | 'google' | 'azure' | 'playht';
export type LLMProvider = 'openai' | 'gemini' | 'anthropic' | 'groq' | 'azure';

export interface TranscriptionResult {
  text: string;
  confidence?: number;
  isFinal: boolean;
  words?: Array<{
    word: string;
    start: number;
    end: number;
    confidence: number;
  }>;
}

export interface LLMMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface LLMResponse {
  content: string;
  finishReason?: 'stop' | 'length' | 'content_filter';
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// Health Check Types
// ═══════════════════════════════════════════════════════════════════════════════

export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy';

export interface DependencyHealth {
  name: string;
  status: HealthStatus;
  latencyMs?: number;
  message?: string;
  lastChecked: Date;
}

export interface HealthCheckResult {
  status: HealthStatus;
  version: string;
  uptime: number;
  timestamp: Date;
  dependencies: DependencyHealth[];
}

// ═══════════════════════════════════════════════════════════════════════════════
// Error Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface AppError extends Error {
  code: string;
  statusCode?: number;
  isOperational: boolean;
  context?: Record<string, unknown>;
}

export interface RetryOptions {
  maxRetries: number;
  baseDelayMs: number;
  maxDelayMs: number;
  backoffMultiplier: number;
  retryCondition?: (error: Error) => boolean;
}

export interface CircuitBreakerOptions {
  failureThreshold: number;
  successThreshold: number;
  timeout: number;
  resetTimeout: number;
}

export type CircuitState = 'closed' | 'open' | 'half-open';

// ═══════════════════════════════════════════════════════════════════════════════
// Logger Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface LogContext {
  correlationId?: string;
  streamId?: string;
  callSid?: string;
  [key: string]: unknown;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  context: string;
  correlationId?: string;
  data?: Record<string, unknown>;
  error?: {
    name: string;
    message: string;
    stack?: string;
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// Connection Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface ConnectionInfo {
  streamId: string;
  clientIp: string;
  userAgent?: string;
  sampleRate: number;
  customParams: Record<string, string>;
  connectedAt: Date;
  authenticated: boolean;
}

export interface ConnectionStats {
  streamId: string;
  mediaChunksReceived: number;
  mediaChunksSent: number;
  duration: number;
  bytesReceived: number;
  bytesSent: number;
}

