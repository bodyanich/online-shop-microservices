import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

// Test configuration
export const options = {
  vus: 5,              // 5 concurrent users
  duration: '2m',      // Run for 2 minutes
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% requests should be below 500ms
    http_req_failed: ['rate<0.05'],     // Error rate should be less than 5%
    errors: ['rate<0.05'],
  },
};

const BASE_PRODUCT_URL = 'http://localhost:8001';
const BASE_ORDER_URL = 'http://localhost:8002';

// Test data
let testProductId = null;

export function setup() {
  console.log('🚀 Starting Smoke Test Setup...');
  
  // Create a test product for orders
  const productPayload = JSON.stringify({
    name: 'K6 Test Product - Laptop',
    description: 'Test product for load testing',
    price: 15999.99,
    stock: 1000,
    category: 'Electronics'
  });
  
  const productRes = http.post(
    `${BASE_PRODUCT_URL}/products`,
    productPayload,
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  if (productRes.status === 201) {
    const product = JSON.parse(productRes.body);
    testProductId = product.id;
    console.log(`✓ Test product created: ID=${testProductId}`);
    return { productId: testProductId };
  } else {
    console.error('✗ Failed to create test product');
    return null;
  }
}

export default function(data) {
  // Skip if setup failed
  if (!data || !data.productId) {
    console.error('Setup failed, skipping test');
    return;
  }
  
  const productId = data.productId;
  
  // Test 1: Health checks
  {
    const productHealth = http.get(`${BASE_PRODUCT_URL}/health`);
    check(productHealth, {
      'Product Service health check': (r) => r.status === 200,
    }) || errorRate.add(1);
    
    const orderHealth = http.get(`${BASE_ORDER_URL}/health`);
    check(orderHealth, {
      'Order Service health check': (r) => r.status === 200,
    }) || errorRate.add(1);
  }
  
  sleep(0.5);
  
  // Test 2: Get all products
  {
    const productsRes = http.get(`${BASE_PRODUCT_URL}/products`);
    const success = check(productsRes, {
      'Get products status 200': (r) => r.status === 200,
      'Get products has data': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.products && body.products.length > 0;
        } catch {
          return false;
        }
      },
      'Get products response time < 200ms': (r) => r.timings.duration < 200,
    });
    
    if (!success) errorRate.add(1);
  }
  
  sleep(0.5);
  
  // Test 3: Get specific product
  {
    const productRes = http.get(`${BASE_PRODUCT_URL}/products/${productId}`);
    const success = check(productRes, {
      'Get product by ID status 200': (r) => r.status === 200,
      'Get product has correct ID': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.id === productId;
        } catch {
          return false;
        }
      },
      'Get product response time < 100ms': (r) => r.timings.duration < 100,
    });
    
    if (!success) errorRate.add(1);
  }
  
  sleep(0.5);
  
  // Test 4: Check stock availability
  {
    const stockRes = http.get(`${BASE_PRODUCT_URL}/products/${productId}/check?quantity=1`);
    const success = check(stockRes, {
      'Check stock status 200': (r) => r.status === 200,
      'Stock is available': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.available === true;
        } catch {
          return false;
        }
      },
    });
    
    if (!success) errorRate.add(1);
  }
  
  sleep(0.5);
  
  // Test 5: Create order (main use case)
  {
    const orderPayload = JSON.stringify({
      product_id: productId,
      quantity: 1,
      customer_email: `customer_${__VU}_${__ITER}@k6test.com`
    });
    
    const orderRes = http.post(
      `${BASE_ORDER_URL}/orders`,
      orderPayload,
      { headers: { 'Content-Type': 'application/json' } }
    );
    
    const success = check(orderRes, {
      'Create order status 201': (r) => r.status === 201,
      'Create order returns order ID': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.id > 0;
        } catch {
          return false;
        }
      },
      'Create order response time < 500ms': (r) => r.timings.duration < 500,
    });
    
    if (!success) errorRate.add(1);
  }
  
  sleep(1);
  
  // Test 6: Get orders
  {
    const ordersRes = http.get(`${BASE_ORDER_URL}/orders`);
    const success = check(ordersRes, {
      'Get orders status 200': (r) => r.status === 200,
      'Get orders response time < 300ms': (r) => r.timings.duration < 300,
    });
    
    if (!success) errorRate.add(1);
  }
  
  sleep(1);
}

export function teardown(data) {
  console.log('🧹 Cleaning up...');
  
  if (data && data.productId) {
    const deleteRes = http.del(`${BASE_PRODUCT_URL}/products/${data.productId}`);
    if (deleteRes.status === 204) {
      console.log(`✓ Test product deleted: ID=${data.productId}`);
    }
  }
  
  console.log('✅ Smoke Test completed!');
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options) {
  const indent = options.indent || '';
  const enableColors = options.enableColors || false;
  
  let summary = '\n' + indent + '📊 Smoke Test Summary\n';
  summary += indent + '═'.repeat(50) + '\n\n';
  
  // Overall statistics
  summary += indent + `Total requests: ${data.metrics.http_reqs.values.count}\n`;
  summary += indent + `Failed requests: ${data.metrics.http_req_failed.values.passes || 0}\n`;
  summary += indent + `Request rate: ${data.metrics.http_reqs.values.rate.toFixed(2)} req/s\n\n`;
  
  // Response times
  summary += indent + 'Response Times:\n';
  summary += indent + `  Average: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms\n`;
  summary += indent + `  Median:  ${data.metrics.http_req_duration.values.med.toFixed(2)}ms\n`;
  summary += indent + `  95th:    ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
  summary += indent + `  Max:     ${data.metrics.http_req_duration.values.max.toFixed(2)}ms\n\n`;
  
  // Thresholds
  summary += indent + 'Thresholds:\n';
  for (const [name, threshold] of Object.entries(data.thresholds)) {
    const passed = threshold.ok ? '✓ PASS' : '✗ FAIL';
    summary += indent + `  ${name}: ${passed}\n`;
  }
  
  summary += '\n' + indent + '═'.repeat(50) + '\n';
  
  return summary;
}