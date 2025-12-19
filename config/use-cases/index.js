/**
 * Use Case Templates Index
 * 
 * Pre-built configurations for common voice bot use cases.
 * 
 * Usage:
 *   const { customerSupport } = require('./config/use-cases');
 *   // Use customerSupport.systemPrompt, customerSupport.voice, etc.
 */

module.exports = {
  customerSupport: require('./customer-support'),
  appointmentBooking: require('./appointment-booking'),
  orderStatus: require('./order-status'),
  
  // Helper to list all available use cases
  list() {
    return [
      { id: 'customerSupport', name: 'Customer Support', voice: 'nova' },
      { id: 'appointmentBooking', name: 'Appointment Booking', voice: 'shimmer' },
      { id: 'orderStatus', name: 'Order Status', voice: 'alloy' }
    ];
  },
  
  // Get a use case by ID
  get(id) {
    return this[id] || null;
  }
};

