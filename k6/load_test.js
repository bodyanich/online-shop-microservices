import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomIntBetween, randomItem } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// Custom metrics
const errorRate = new Rate('errors');
const orderCreationTime = new Trend('order_creation_duration');
const productFetchTime = new Trend('product_fetch_duration');
const stockCheckTime = new Trend('stock_check_duration');
const successfulOrders = new Counter('successful_orders');
const failedOrders = new Counter('failed_orders');

// Test configuration with stages
export const options = {
  stages: [
    { duration: '1m', target: 20 },   // Ramp-up to 20 users over 1 minute
    { duration: '3m', target: 50 },   // Ramp-up to 50 users over 3 minutes
    { duration: '5m', target: 50 },   // Stay at 50 users for 5 minutes
    { duration: '2m', target: 100 },  // Spike to 100 users for 2 minutes
    { duration: '3m', target: 50 },   // Scale down to 50 users
    { duration: '2m', target: 0 },    // Ramp-down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000', 'p(99)<2000'],  // 95% < 1s, 99% < 2s
    http_req_failed: ['rate<0.10'],                    // Error rate < 10%
    errors: ['rate<0.10'],
    order_creation_duration: ['p(95)<800'],            // Order creation < 800ms at p95
    product_fetch_duration: ['p(95)<200'],             // Product fetch < 200ms at p95
    stock_check_duration: ['p(95)<150'],               // Stock check < 150ms at p95
    successful_orders: ['count>100'],                  // At least 100 successful orders
  },
};

//const BASE_PRODUCT_URL = 'http://localhost:8001';
//const BASE_ORDER_URL = 'http://localhost:8002';

const BASE_PRODUCT_URL = 'http://host.docker.internal:8001';
const BASE_ORDER_URL = 'http://host.docker.internal:8002';

// Test data
const categories = ['Electronics', 'Accessories', 'Audio', 'Computing'];
let testProducts = [];

export function setup() {
  console.log('Starting Load Test Setup...');
  console.log('Creating test products...');
  
  const products = [];
  
  // Create 10 test products
  for (let i = 1; i <= 10; i++) {
    const productPayload = JSON.stringify({
      name: `K6 Load Test Product ${i}`,
      description: `Product ${i} for load testing - ${categories[i % categories.length]}`,
      price: randomIntBetween(1000, 50000),
      stock: 10000,  // High stock to avoid conflicts
      category: categories[i % categories.length]
    });
    
    const productRes = http.post(
      `${BASE_PRODUCT_URL}/products`,
      productPayload,
      { headers: { 'Content-Type': 'application/json' } }
    );
    
    if (productRes.status === 201) {
      const product = JSON.parse(productRes.body);
      products.push(product.id);
      console.log(`✓ Product ${i}/10 created: ID=${product.id}`);
    } else {
      console.error(`✗ Failed to create product ${i}`);
    }
    
    sleep(0.1);
  }
  
  console.log(`Setup complete: ${products.length} products created`);
  return { productIds: products };
}

export default function(data) {
  // Skip if setup failed
  if (!data || !data.productIds || data.productIds.length === 0) {
    console.error('Setup failed, skipping test');
    return;
  }
  
  const productIds = data.productIds;
  
  // Scenario 1: Browse products (40% of users)
  if (Math.random() < 0.4) {
    browseProducts(productIds);
  }
  
  // Scenario 2: Create order (30% of users)
  else if (Math.random() < 0.7) {
    createOrder(productIds);
  }
  
  // Scenario 3: Check orders (20% of users)
  else if (Math.random() < 0.9) {
    checkOrders();
  }
  
  // Scenario 4: Mixed workflow (10% of users)
  else {
    mixedWorkflow(productIds);
  }
}

// Scenario 1: Browse products
function browseProducts(productIds) {
  group('Browse Products', function() {
    // Get all products
    const start1 = Date.now();
    const allProductsRes = http.get(`${BASE_PRODUCT_URL}/products?limit=50`);
    productFetchTime.add(Date.now() - start1);
    
    const success1 = check(allProductsRes, {
      'Browse: Get products status 200': (r) => r.status === 200,
      'Browse: Products list not empty': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.products && body.products.length > 0;
        } catch {
          return false;
        }
      },
    });
    
    if (!success1) errorRate.add(1);
    
    sleep(randomIntBetween(1, 3));
    
    // Get specific product details
    const randomProductId = randomItem(productIds);
    const start2 = Date.now();
    const productRes = http.get(`${BASE_PRODUCT_URL}/products/${randomProductId}`);
    productFetchTime.add(Date.now() - start2);
    
    const success2 = check(productRes, {
      'Browse: Get product details status 200': (r) => r.status === 200,
    });
    
    if (!success2) errorRate.add(1);
    
    sleep(randomIntBetween(1, 2));
  });
}

// Scenario 2: Create order (main use case)
function createOrder(productIds) {
  group('Create Order', function() {
    const productId = randomItem(productIds);
    const quantity = randomIntBetween(1, 3);
    
    // Step 1: Check product availability
    const start1 = Date.now();
    const productRes = http.get(`${BASE_PRODUCT_URL}/products/${productId}`);
    productFetchTime.add(Date.now() - start1);
    
    check(productRes, {
      'Order: Get product status 200': (r) => r.status === 200,
    }) || errorRate.add(1);
    
    sleep(0.5);
    
    // Step 2: Check stock
    const start2 = Date.now();
    const stockRes = http.get(
      `${BASE_PRODUCT_URL}/products/${productId}/check?quantity=${quantity}`
    );
    stockCheckTime.add(Date.now() - start2);
    
    const stockAvailable = check(stockRes, {
      'Order: Stock check status 200': (r) => r.status === 200,
      'Order: Stock available': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.available === true;
        } catch {
          return false;
        }
      },
    });
    
    if (!stockAvailable) {
      errorRate.add(1);
      return;
    }
    
    sleep(0.5);
    
    // Step 3: Create order
    const orderPayload = JSON.stringify({
      product_id: productId,
      quantity: quantity,
      customer_email: `customer_${__VU}_${__ITER}@k6load.com`
    });
    
    const start3 = Date.now();
    const orderRes = http.post(
      `${BASE_ORDER_URL}/orders`,
      orderPayload,
      { headers: { 'Content-Type': 'application/json' } }
    );
    const orderDuration = Date.now() - start3;
    orderCreationTime.add(orderDuration);
    
    const orderSuccess = check(orderRes, {
      'Order: Create order status 201': (r) => r.status === 201,
      'Order: Returns order ID': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.id > 0;
        } catch {
          return false;
        }
      },
      'Order: Has correct product ID': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.product_id === productId;
        } catch {
          return false;
        }
      },
    });
    
    if (orderSuccess) {
      successfulOrders.add(1);
    } else {
      failedOrders.add(1);
      errorRate.add(1);
    }
    
    sleep(1);
  });
}

// Scenario 3: Check orders
function checkOrders() {
  group('Check Orders', function() {
    // Get all orders
    const ordersRes = http.get(`${BASE_ORDER_URL}/orders?limit=20`);
    
    check(ordersRes, {
      'Check: Get orders status 200': (r) => r.status === 200,
      'Check: Response time < 500ms': (r) => r.timings.duration < 500,
    }) || errorRate.add(1);
    
    sleep(randomIntBetween(2, 4));
  });
}

// Scenario 4: Mixed workflow
function mixedWorkflow(productIds) {
  group('Mixed Workflow', function() {
    // Browse products
    http.get(`${BASE_PRODUCT_URL}/products?limit=20`);
    sleep(1);
    
    // Check specific product
    const productId = randomItem(productIds);
    http.get(`${BASE_PRODUCT_URL}/products/${productId}`);
    sleep(1);
    
    // Check stock
    http.get(`${BASE_PRODUCT_URL}/products/${productId}/check?quantity=1`);
    sleep(0.5);
    
    // Create order
    const orderPayload = JSON.stringify({
      product_id: productId,
      quantity: 1,
      customer_email: `mixed_${__VU}_${__ITER}@k6load.com`
    });
    
    const start = Date.now();
    const orderRes = http.post(
      `${BASE_ORDER_URL}/orders`,
      orderPayload,
      { headers: { 'Content-Type': 'application/json' } }
    );
    orderCreationTime.add(Date.now() - start);
    
    if (orderRes.status === 201) {
      successfulOrders.add(1);
      
      // Check orders list
      sleep(1);
      http.get(`${BASE_ORDER_URL}/orders?limit=10`);
    } else {
      failedOrders.add(1);
      errorRate.add(1);
    }
    
    sleep(2);
  });
}

export function teardown(data) {
  console.log('\nCleaning up test data...');
  
  if (data && data.productIds) {
    let deleted = 0;
    for (const productId of data.productIds) {
      const deleteRes = http.del(`${BASE_PRODUCT_URL}/products/${productId}`);
      if (deleteRes.status === 204) {
        deleted++;
      }
      sleep(0.1);
    }
    console.log(`✓ Deleted ${deleted}/${data.productIds.length} test products`);
  }
  
  console.log('Load Test completed!');
}

export function handleSummary(data) {
  console.log('\n' + '═'.repeat(70));
  console.log('LOAD TEST SUMMARY REPORT');
  console.log('═'.repeat(70) + '\n');
  
  // Test duration
  const duration = (data.state.testRunDurationMs / 1000).toFixed(2);
  console.log(`Test Duration: ${duration} seconds\n`);
  
  // Overall statistics
  console.log('Overall Statistics:');
  console.log(`   Total HTTP Requests: ${data.metrics.http_reqs.values.count}`);
  console.log(`   Request Rate: ${data.metrics.http_reqs.values.rate.toFixed(2)} req/s`);
  console.log(`   Failed Requests: ${data.metrics.http_req_failed.values.passes || 0} (${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%)`);
  console.log(`   Successful Orders: ${data.metrics.successful_orders?.values.count || 0}`);
  console.log(`   Failed Orders: ${data.metrics.failed_orders?.values.count || 0}\n`);
  
  // Response times
  console.log('Response Times (HTTP Requests):');
  console.log(`   Average: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms`);
  console.log(`   Median:  ${data.metrics.http_req_duration.values.med.toFixed(2)}ms`);
  console.log(`   90th:    ${data.metrics.http_req_duration.values['p(90)'].toFixed(2)}ms`);
  console.log(`   95th:    ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
  console.log(`   99th:    ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms`);
  console.log(`   Max:     ${data.metrics.http_req_duration.values.max.toFixed(2)}ms\n`);
  
  // Custom metrics
  if (data.metrics.order_creation_duration) {
    console.log('Order Creation Times:');
    console.log(`   Average: ${data.metrics.order_creation_duration.values.avg.toFixed(2)}ms`);
    console.log(`   95th:    ${data.metrics.order_creation_duration.values['p(95)'].toFixed(2)}ms`);
    console.log(`   99th:    ${data.metrics.order_creation_duration.values['p(99)'].toFixed(2)}ms\n`);
  }
  
  if (data.metrics.product_fetch_duration) {
    console.log('Product Fetch Times:');
    console.log(`   Average: ${data.metrics.product_fetch_duration.values.avg.toFixed(2)}ms`);
    console.log(`   95th:    ${data.metrics.product_fetch_duration.values['p(95)'].toFixed(2)}ms\n`);
  }
  
  if (data.metrics.stock_check_duration) {
    console.log('Stock Check Times:');
    console.log(`   Average: ${data.metrics.stock_check_duration.values.avg.toFixed(2)}ms`);
    console.log(`   95th:    ${data.metrics.stock_check_duration.values['p(95)'].toFixed(2)}ms\n`);
  }
  
  // Virtual Users
  console.log('Virtual Users:');
  console.log(`   Max VUs: ${data.metrics.vus_max.values.max}`);
  console.log(`   Avg VUs: ${data.metrics.vus.values.value.toFixed(2)}\n`);
  
  // Thresholds
  console.log('Thresholds:');
  let allPassed = true;
  for (const [name, threshold] of Object.entries(data.thresholds)) {
    const status = threshold.ok ? '✓ PASS' : '✗ FAIL';
    const color = threshold.ok ? '' : '❌ ';
    console.log(`   ${color}${name}: ${status}`);
    if (!threshold.ok) allPassed = false;
  }
  
  console.log('\n' + '═'.repeat(70));
  if (allPassed) {
    console.log('All thresholds passed! System is performing well under load.');
  } else {
    console.log('Some thresholds failed. Review the metrics above.');
  }
  console.log('═'.repeat(70) + '\n');
  
  return {
    'stdout': '',  // We already printed everything
  };
}