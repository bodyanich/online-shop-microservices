/**
 * K6 Load Test - Order Creation Flow
 * 
 * Scenario: Simulate realistic user behavior creating orders
 * 
 * Test stages:
 * 1. Ramp-up: 0 → 10 users over 30s
 * 2. Sustained load: 10 users for 2 min
 * 3. Peak load: 10 → 30 users over 30s
 * 4. Peak sustained: 30 users for 1 min
 * 5. Ramp-down: 30 → 0 users over 30s
 * 
 * Run: k6 run load-test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const orderCreationRate = new Rate('order_creation_success');
const orderCreationDuration = new Trend('order_creation_duration');
const productFetchDuration = new Trend('product_fetch_duration');
const orderFailures = new Counter('order_failures');

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 10 },  // Ramp-up to 10 users
    { duration: '2m', target: 10 },   // Stay at 10 users
    { duration: '30s', target: 30 },  // Spike to 30 users
    { duration: '1m', target: 30 },   // Stay at 30 users
    { duration: '30s', target: 0 },   // Ramp-down to 0 users
  ],
  thresholds: {
    // HTTP request duration should be below 500ms for 95% of requests
    'http_req_duration': ['p(95)<500'],
    
    // Order creation should succeed at least 95% of the time
    'order_creation_success': ['rate>0.95'],
    
    // Less than 5% of requests should fail
    'http_req_failed': ['rate<0.05'],
    
    // Product fetch should be fast (under 200ms for 90%)
    'product_fetch_duration': ['p(90)<200'],
  },
};

// Base URLs
const PRODUCT_SERVICE_URL = 'http://localhost:8001';
const ORDER_SERVICE_URL = 'http://localhost:8002';

// Test data - product IDs to use for orders
const PRODUCT_IDS = [1, 2, 3, 4, 5];

// Generate random email
function randomEmail() {
  const timestamp = Date.now();
  const random = Math.floor(Math.random() * 10000);
  return `test.user.${timestamp}.${random}@example.com`;
}

// Get random product ID
function randomProductId() {
  return PRODUCT_IDS[Math.floor(Math.random() * PRODUCT_IDS.length)];
}

// Get random quantity (1-3)
function randomQuantity() {
  return Math.floor(Math.random() * 3) + 1;
}

export function setup() {
  console.log('🚀 Starting load test...');
  console.log(`📍 Product Service: ${PRODUCT_SERVICE_URL}`);
  console.log(`📍 Order Service: ${ORDER_SERVICE_URL}`);
  
  // Health check
  const healthCheck = http.get(`${ORDER_SERVICE_URL}/health`);
  if (healthCheck.status !== 200) {
    console.error('❌ Order Service is not healthy!');
    throw new Error('Order Service health check failed');
  }
  
  console.log('✅ Services are healthy. Starting test...');
}

export default function () {
  // Step 1: Get list of products (browsing behavior)
  const productsResponse = http.get(`${PRODUCT_SERVICE_URL}/products`, {
    tags: { name: 'GetProducts' },
  });
  
  check(productsResponse, {
    'products list fetched': (r) => r.status === 200,
  });
  
  productFetchDuration.add(productsResponse.timings.duration);
  
  // Simulate user reading the product list
  sleep(1 + Math.random() * 2); // 1-3 seconds
  
  // Step 2: Get specific product details
  const productId = randomProductId();
  const productResponse = http.get(`${PRODUCT_SERVICE_URL}/products/${productId}`, {
    tags: { name: 'GetProduct' },
  });
  
  check(productResponse, {
    'product details fetched': (r) => r.status === 200,
  });
  
  // Simulate user reading product details
  sleep(2 + Math.random() * 3); // 2-5 seconds
  
  // Step 3: Create order
  const orderPayload = JSON.stringify({
    product_id: productId,
    quantity: randomQuantity(),
    customer_email: randomEmail(),
  });
  
  const orderHeaders = {
    'Content-Type': 'application/json',
  };
  
  const startTime = Date.now();
  const orderResponse = http.post(
    `${ORDER_SERVICE_URL}/orders`,
    orderPayload,
    {
      headers: orderHeaders,
      tags: { name: 'CreateOrder' },
    }
  );
  const duration = Date.now() - startTime;
  
  // Check order creation
  const orderSuccess = check(orderResponse, {
    'order created successfully': (r) => r.status === 201,
    'order has id': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.id !== undefined;
      } catch (e) {
        return false;
      }
    },
    'order has correct status': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.status === 'pending';
      } catch (e) {
        return false;
      }
    },
  });
  
  // Record metrics
  orderCreationRate.add(orderSuccess);
  orderCreationDuration.add(duration);
  
  if (!orderSuccess) {
    orderFailures.add(1);
    console.log(`❌ Order creation failed: ${orderResponse.status} - ${orderResponse.body}`);
  }
  
  // Step 4: Get order details (verify creation)
  if (orderResponse.status === 201) {
    try {
      const orderData = JSON.parse(orderResponse.body);
      const orderId = orderData.id;
      
      sleep(0.5); // Small delay
      
      const getOrderResponse = http.get(`${ORDER_SERVICE_URL}/orders/${orderId}`, {
        tags: { name: 'GetOrder' },
      });
      
      check(getOrderResponse, {
        'order retrieved successfully': (r) => r.status === 200,
      });
    } catch (e) {
      console.log(`❌ Error parsing order response: ${e}`);
    }
  }
  
  // Simulate user thinking time before next action
  sleep(3 + Math.random() * 5); // 3-8 seconds
}

export function teardown(data) {
  console.log('🏁 Load test completed!');
  console.log('📊 Check the summary for detailed metrics.');
}

/**
 * Expected Results:
 * 
 * Success Criteria:
 * - p(95) response time < 500ms
 * - Order creation success rate > 95%
 * - HTTP failure rate < 5%
 * - Product fetch p(90) < 200ms
 * 
 * If tests fail:
 * 1. Check service logs: docker-compose logs -f order-service
 * 2. Check database connections
 * 3. Check RabbitMQ queue sizes
 * 4. Monitor CPU/Memory usage
 * 5. Consider scaling services (docker-compose up --scale order-service=2)
 */