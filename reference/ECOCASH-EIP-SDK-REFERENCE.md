# EcoCash Instant Payment — SDKs & Code Reference

> **Source of truth:** EcoCash Developer Portal → EcoCash Instant Payment → **SDKs & Codegen** tab (page heading: **SDKs & Code Examples**) — and nothing else
> "Ready-to-run integration code for EcoCash Instant Payment — pick your language and copy."
> **Last verified against the live SDKs & Codegen tab:** 21 September 2026 — 75 of 75 code panels match (whitespace-insensitive SHA-256 comparison). See [Note 11](#note-11--verification-log).

> **Scope.** This document reflects only the SDKs & Codegen tab. It takes no content from any other
> tab or page of the portal, and it is not reconciled against them. All review notes compare the
> tab's samples only with each other. The Documentation tab is covered separately, on the same
> basis, in `ECOCASH-EIP-API.md`.

**Base URL (all languages):**

```
https://developers.ecocash.co.zw/sandbox/payment/v1
```

**Auth (all languages):** HTTP Basic Auth — `Basic base64(username:password)`

**Key Endpoints (shown on every language page):**

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/transactions/amount/` | Initiate payment |
| `GET` | `/{endUserId}/transactions/amount/{clientCorrelator}` | Check status |
| `POST` | `/transactions/refund/` | Refund a payment |

Every language page follows the identical five-step structure: **1 — Install**, **2 — Client Setup**, **3 — Initiate Payment**, **4 — Check Status**, **5 — Refund Transaction**.

---

## Contents

| Language | Client variants |
|---|---|
| [☕ Java](#-java) | [WebClient](#java--1-webclient-spring-webflux--reactive) · [RestClient](#java--2-restclient-spring-61--synchronous) · [Feign Client](#java--3-feign-client-spring-cloud--declarative) |
| [🐘 PHP / Laravel](#-php--laravel) | [Guzzle HTTP](#php--1-guzzle-http-psr-7--direct) · [Http Facade](#http-facade) · [Symfony Http](#symfony-http) |
| [⚡ JavaScript](#-javascript) | [Axios](#axios) · [Fetch API](#fetch-api) · [Got](#got) |
| [⬡ C#](#-c) | [HttpClient](#httpclient) · [RestSharp](#restsharp) · [Refit](#refit) |
| [🐍 Python](#-python) | [Requests](#requests) · [HTTPX](#httpx) · [aiohttp](#aiohttp) |

> ⚠️ **Read before copying:** the code below is reproduced verbatim, including the tab's own inconsistencies and defects. The samples read the transaction status under two different names (Note 2). Several base-URL / path combinations drop `/sandbox/payment/v1` (Note 5). Two C# samples will not compile or authenticate as published (Note 8). See [Cross-cutting notes](#cross-cutting-notes-and-corrections).

> **Reproduction note:** where the portal presents several artefacts inside a single code panel (for example `pom.xml`, Gradle and `application.yml` together under *1 — Install*), this document splits them into separate fenced blocks with the correct language tag. No content is added or removed by that split. Comment markers are kept exactly as the portal prints them — including `# appsettings.json` in the C# install panels, even though that sits above a JSON block.

---

## ☕ Java

**Section label:** SPRING CLIENT

| Variant | Tagline |
|---|---|
| WebClient | Spring WebFlux · Reactive |
| RestClient | Spring 6.1+ · Synchronous |
| Feign Client | Spring Cloud · Declarative |

---

### Java — 1. WebClient (Spring WebFlux · Reactive)

#### 1 — Install

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webflux</artifactId>
</dependency>
```

```groovy
// Gradle — build.gradle
implementation 'org.springframework.boot:spring-boot-starter-webflux'
```

```yaml
# application.yml
eip:
  base-url: https://developers.ecocash.co.zw/sandbox/payment/v1
  username: ${EIP_USERNAME}
  password: ${EIP_PASSWORD}
```

#### 2 — Client Setup

```java
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.client.WebClient;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

@Configuration
public class EIPWebClientConfig {

    @Value("${eip.base-url}") private String baseUrl;
    @Value("${eip.username}") private String username;
    @Value("${eip.password}") private String password;

    @Bean
    public WebClient eipWebClient(WebClient.Builder builder) {
        String token = Base64.getEncoder().encodeToString(
                (username + ":" + password).getBytes(StandardCharsets.UTF_8));

        return builder
                .baseUrl(baseUrl)
                .defaultHeader(HttpHeaders.AUTHORIZATION, "Basic " + token)
                .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .defaultHeader(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
                .build();
    }
}
```

#### 3 — Initiate Payment

```java
@Service
@RequiredArgsConstructor
public class EIPService {

    private final WebClient eipWebClient;

    public Mono<TransactionResponse> initiatePayment(PaymentRequest request) {
        return eipWebClient.post()
                .uri("/transactions/amount/")
                .bodyValue(request)
                .retrieve()
                .onStatus(HttpStatusCode::isError, res ->
                        res.bodyToMono(String.class)
                           .flatMap(body -> Mono.error(
                                   new RuntimeException("EIP error: " + body))))
                .bodyToMono(TransactionResponse.class);
    }
}

// ── Usage ────────────────────────────────────────────────────
PaymentRequest req = PaymentRequest.builder()
        .clientCorrelator("REF-001")
        .notifyUrl("https://yourapp.com/webhook/eip")
        .referenceCode("INV-2024-001")
        .tranType("MER").endUserId("263771234567")
        .remarks("Online Payment").transactionOperationStatus("Charged")
        .paymentAmount(PaymentAmount.builder()
                .charginginformation(ChargingInfo.builder()
                        .amount("5.00").currency("ZWG").description("Online Payment")
                        .build())
                .chargeMetaData(new ChargeMetaData("WEB"))
                .build())
        .merchantCode("287164").merchantPin("1234").merchantNumber("778503033")
        .countryCode("ZW").terminalID("TERM001").location("Harare")
        .superMerchantName("EcoCash Sandbox").merchantName("Test Merchant")
        .build();

TransactionResponse tx = eipService.initiatePayment(req).block();
```

#### 4 — Check Status

```java
public Mono<TransactionResponse> getTransactionStatus(
        String endUserId, String clientCorrelator) {
    return eipWebClient.get()
            .uri("/{endUserId}/transactions/amount/{clientCorrelator}",
                    endUserId, clientCorrelator)
            .retrieve()
            .onStatus(HttpStatusCode::isError, res ->
                    res.bodyToMono(String.class)
                       .flatMap(body -> Mono.error(
                               new RuntimeException("EIP error: " + body))))
            .bodyToMono(TransactionResponse.class);
}

// ── Usage ────────────────────────────────────────────────────
TransactionResponse status = eipService
        .getTransactionStatus("263771234567", "REF-001").block();
System.out.println(status.getTransactionStatus()); // SUCCESS | FAILED | PENDING
```

#### 5 — Refund Transaction

```java
public Mono<TransactionResponse> refundTransaction(RefundRequest request) {
    return eipWebClient.post()
            .uri("/transactions/refund/")
            .bodyValue(request)
            .retrieve()
            .onStatus(HttpStatusCode::isError, res ->
                    res.bodyToMono(String.class)
                       .flatMap(body -> Mono.error(
                               new RuntimeException("EIP error: " + body))))
            .bodyToMono(TransactionResponse.class);
}

// ── Usage ────────────────────────────────────────────────────
RefundRequest req = RefundRequest.builder()
        .clientCorrelator("REFUND-001")
        .referenceCode("REF-INV-2024-001")
        .tranType("MER").endUserId("263771234567")
        .originalEcocashReference("MP240601.1200.T0123456")
        .paymentAmount(PaymentAmount.builder()
                .charginginformation(ChargingInfo.builder()
                        .amount("5.00").currency("ZWG").description("Refund")
                        .build())
                .chargeMetaData(new ChargeMetaData("WEB"))
                .build())
        .merchantCode("287164").merchantPin("1234").merchantNumber("778503033")
        .countryCode("ZW").terminalID("TERM001").location("Harare")
        .superMerchantName("EcoCash Sandbox").merchantName("Test Merchant")
        .currencyCode("ZWG").remarks("Refund")
        .build();

TransactionResponse refund = eipService.refundTransaction(req).block();
```

---

### Java — 2. RestClient (Spring 6.1+ · Synchronous)

#### 1 — Install

```xml
<!-- pom.xml — Spring Boot 3.2 / Spring Framework 6.1+ required -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

```groovy
// Gradle — build.gradle
implementation 'org.springframework.boot:spring-boot-starter-web'
```

```yaml
# application.yml
eip:
  base-url: https://developers.ecocash.co.zw/sandbox/payment/v1
  username: ${EIP_USERNAME}
  password: ${EIP_PASSWORD}
```

#### 2 — Client Setup

```java
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

@Configuration
public class EIPRestClientConfig {

    @Value("${eip.base-url}") private String baseUrl;
    @Value("${eip.username}") private String username;
    @Value("${eip.password}") private String password;

    @Bean
    public RestClient eipRestClient(RestClient.Builder builder) {
        String token = Base64.getEncoder().encodeToString(
                (username + ":" + password).getBytes(StandardCharsets.UTF_8));

        return builder
                .baseUrl(baseUrl)
                .defaultHeader(HttpHeaders.AUTHORIZATION, "Basic " + token)
                .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .defaultHeader(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
                .build();
    }
}
```

#### 3 — Initiate Payment

```java
@Service
@RequiredArgsConstructor
public class EIPService {

    private final RestClient eipRestClient;

    public TransactionResponse initiatePayment(PaymentRequest request) {
        return eipRestClient.post()
                .uri("/transactions/amount/")
                .body(request)
                .retrieve()
                .onStatus(HttpStatusCode::isError, (req, res) -> {
                    throw new RuntimeException(
                            "EIP error: HTTP " + res.getStatusCode());
                })
                .body(TransactionResponse.class);
    }
}

// ── Usage ────────────────────────────────────────────────────
PaymentRequest req = PaymentRequest.builder()
        .clientCorrelator("REF-001")
        .notifyUrl("https://yourapp.com/webhook/eip")
        .referenceCode("INV-2024-001")
        .tranType("MER").endUserId("263771234567")
        .remarks("Online Payment").transactionOperationStatus("Charged")
        .paymentAmount(PaymentAmount.builder()
                .charginginformation(ChargingInfo.builder()
                        .amount("5.00").currency("ZWG").description("Online Payment")
                        .build())
                .chargeMetaData(new ChargeMetaData("WEB"))
                .build())
        .merchantCode("287164").merchantPin("1234").merchantNumber("778503033")
        .countryCode("ZW").terminalID("TERM001").location("Harare")
        .superMerchantName("EcoCash Sandbox").merchantName("Test Merchant")
        .build();

TransactionResponse tx = eipService.initiatePayment(req);
```

#### 4 — Check Status

```java
public TransactionResponse getTransactionStatus(
        String endUserId, String clientCorrelator) {
    return eipRestClient.get()
            .uri("/{endUserId}/transactions/amount/{clientCorrelator}",
                    endUserId, clientCorrelator)
            .retrieve()
            .onStatus(HttpStatusCode::isError, (req, res) -> {
                throw new RuntimeException(
                        "EIP error: HTTP " + res.getStatusCode());
            })
            .body(TransactionResponse.class);
}

// ── Usage ────────────────────────────────────────────────────
TransactionResponse status =
        eipService.getTransactionStatus("263771234567", "REF-001");
System.out.println(status.getTransactionStatus()); // SUCCESS | FAILED | PENDING
```

#### 5 — Refund Transaction

```java
public TransactionResponse refundTransaction(RefundRequest request) {
    return eipRestClient.post()
            .uri("/transactions/refund/")
            .body(request)
            .retrieve()
            .onStatus(HttpStatusCode::isError, (req, res) -> {
                throw new RuntimeException(
                        "EIP error: HTTP " + res.getStatusCode());
            })
            .body(TransactionResponse.class);
}

// ── Usage ────────────────────────────────────────────────────
RefundRequest req = RefundRequest.builder()
        .clientCorrelator("REFUND-001")
        .referenceCode("REF-INV-2024-001")
        .tranType("MER").endUserId("263771234567")
        .originalEcocashReference("MP240601.1200.T0123456")
        .paymentAmount(PaymentAmount.builder()
                .charginginformation(ChargingInfo.builder()
                        .amount("5.00").currency("ZWG").description("Refund")
                        .build())
                .chargeMetaData(new ChargeMetaData("WEB"))
                .build())
        .merchantCode("287164").merchantPin("1234").merchantNumber("778503033")
        .countryCode("ZW").terminalID("TERM001").location("Harare")
        .superMerchantName("EcoCash Sandbox").merchantName("Test Merchant")
        .currencyCode("ZWG").remarks("Refund")
        .build();

TransactionResponse refund = eipService.refundTransaction(req);
```

---

### Java — 3. Feign Client (Spring Cloud · Declarative)

#### 1 — Install

```xml
<!-- pom.xml — also add Spring Cloud BOM to <dependencyManagement> -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-openfeign</artifactId>
</dependency>
```

```groovy
// Gradle
implementation 'org.springframework.cloud:spring-cloud-starter-openfeign'
```

```yaml
# application.yml
eip:
  base-url: https://developers.ecocash.co.zw/sandbox/payment/v1
  username: ${EIP_USERNAME}
  password: ${EIP_PASSWORD}
```

#### 2 — Client Setup

```java
// 1. Enable Feign in your main application class
@SpringBootApplication
@EnableFeignClients
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}

// 2. Basic Auth request interceptor
public class EIPFeignConfig {

    @Value("${eip.username}") private String username;
    @Value("${eip.password}") private String password;

    @Bean
    public RequestInterceptor eipBasicAuthInterceptor() {
        return template -> {
            String token = Base64.getEncoder().encodeToString(
                    (username + ":" + password).getBytes(StandardCharsets.UTF_8));
            template.header("Authorization", "Basic " + token);
            template.header("Content-Type", "application/json");
        };
    }
}

// 3. Declare the client interface — no implementation needed
@FeignClient(
        name = "eip-client",
        url = "${eip.base-url}",
        configuration = EIPFeignConfig.class
)
public interface EIPFeignClient {

    @PostMapping("/transactions/amount/")
    TransactionResponse initiatePayment(@RequestBody PaymentRequest request);

    @GetMapping("/{endUserId}/transactions/amount/{clientCorrelator}")
    TransactionResponse getTransactionStatus(
            @PathVariable("endUserId") String endUserId,
            @PathVariable("clientCorrelator") String clientCorrelator);

    @PostMapping("/transactions/refund/")
    TransactionResponse refundTransaction(@RequestBody RefundRequest request);
}
```

#### 3 — Initiate Payment

```java
@Service
@RequiredArgsConstructor
public class PaymentService {

    private final EIPFeignClient eipClient;

    public TransactionResponse pay(String endUserId) {
        PaymentRequest request = PaymentRequest.builder()
                .clientCorrelator("REF-" + System.currentTimeMillis())
                .notifyUrl("https://yourapp.com/webhook/eip")
                .referenceCode("INV-2024-001")
                .tranType("MER").endUserId(endUserId)
                .remarks("Online Payment").transactionOperationStatus("Charged")
                .paymentAmount(PaymentAmount.builder()
                        .charginginformation(ChargingInfo.builder()
                                .amount("5.00").currency("ZWG").description("Online Payment")
                                .build())
                        .chargeMetaData(new ChargeMetaData("WEB"))
                        .build())
                .merchantCode("287164").merchantPin("1234").merchantNumber("778503033")
                .countryCode("ZW").terminalID("TERM001").location("Harare")
                .superMerchantName("EcoCash Sandbox").merchantName("Test Merchant")
                .build();

        return eipClient.initiatePayment(request);
    }
}
```

#### 4 — Check Status

```java
public TransactionResponse getStatus(String endUserId, String correlator) {
    return eipClient.getTransactionStatus(endUserId, correlator);
}

// ── Usage ────────────────────────────────────────────────────
TransactionResponse status =
        paymentService.getStatus("263771234567", "REF-001");
System.out.println(status.getTransactionStatus()); // SUCCESS | FAILED | PENDING
```

#### 5 — Refund Transaction

```java
public TransactionResponse refund(String endUserId, String ecocashRef) {
    RefundRequest request = RefundRequest.builder()
            .clientCorrelator("REFUND-" + System.currentTimeMillis())
            .referenceCode("REF-INV-2024-001")
            .tranType("MER").endUserId(endUserId)
            .originalEcocashReference(ecocashRef)
            .paymentAmount(PaymentAmount.builder()
                    .charginginformation(ChargingInfo.builder()
                            .amount("5.00").currency("ZWG").description("Refund")
                            .build())
                    .chargeMetaData(new ChargeMetaData("WEB"))
                    .build())
            .merchantCode("287164").merchantPin("1234").merchantNumber("778503033")
            .countryCode("ZW").terminalID("TERM001").location("Harare")
            .superMerchantName("EcoCash Sandbox").merchantName("Test Merchant")
            .currencyCode("ZWG").remarks("Refund")
            .build();

    return eipClient.refundTransaction(request);
}

// ── Usage ────────────────────────────────────────────────────
TransactionResponse refund =
        paymentService.refund("263771234567", "MP240601.1200.T0123456");
```

---

## 🐘 PHP / Laravel

**Section label:** HTTP CLIENT

| Variant | Tagline |
|---|---|
| Guzzle HTTP | PSR-7 · Direct |
| Http Facade | Laravel built-in · Fluent |
| Symfony Http | PSR-18 · Framework-agnostic |

---

### PHP — 1. Guzzle HTTP (PSR-7 · Direct)

#### 1 — Install

```bash
# Install via Composer
composer require guzzlehttp/guzzle

# .env
EIP_BASE_URL=https://developers.ecocash.co.zw/sandbox/payment/v1
EIP_USERNAME=your_username
EIP_PASSWORD=your_password
```

#### 2 — Client Setup

```php
<?php
// config/eip.php
return [
    'base_url' => env('EIP_BASE_URL',
        'https://developers.ecocash.co.zw/sandbox/payment/v1'),
    'username' => env('EIP_USERNAME'),
    'password' => env('EIP_PASSWORD'),
];

// ── app/Services/EcoCashEIPService.php ───────────────────────
namespace App\Services;

use GuzzleHttp\Client;
use GuzzleHttp\Exception\RequestException;

class EcoCashEIPService
{
    private Client $client;

    public function __construct()
    {
        $this->client = new Client([
            'base_uri' => config('eip.base_url'),
            'auth'     => [config('eip.username'), config('eip.password')],
            'headers'  => [
                'Content-Type' => 'application/json',
                'Accept'       => 'application/json',
            ],
            'timeout'  => 30,
        ]);
    }
}
```

#### 3 — Initiate Payment

```php
public function initiatePayment(array $data): array
{
    try {
        $response = $this->client->post('/transactions/amount/', [
            'json' => $data,
        ]);
        return json_decode($response->getBody()->getContents(), true);
    } catch (RequestException $e) {
        return ['error' => $e->getMessage(), 'status' => $e->getResponse()?->getStatusCode()];
    }
}

// ── Usage ────────────────────────────────────────────────────
$service = app(\App\Services\EcoCashEIPService::class);

$result = $service->initiatePayment([
    'clientCorrelator'           => 'REF-001',
    'notifyUrl'                  => 'https://yourapp.com/webhook/eip',
    'referenceCode'              => 'INV-2024-001',
    'tranType'                   => 'MER',
    'endUserId'                  => '263771234567',
    'remarks'                    => 'Online Payment',
    'transactionOperationStatus' => 'Charged',
    'paymentAmount'              => [
        'charginginformation' => [
            'amount'      => '5.00',
            'currency'    => 'ZWG',
            'description' => 'Online Payment',
        ],
        'chargeMetaData' => ['channel' => 'WEB'],
    ],
    'merchantCode'      => '287164',
    'merchantPin'       => '1234',
    'merchantNumber'    => '778503033',
    'countryCode'       => 'ZW',
    'terminalID'        => 'TERM001',
    'location'          => 'Harare',
    'superMerchantName' => 'EcoCash Sandbox',
    'merchantName'      => 'Test Merchant',
]);
```

#### 4 — Check Status

```php
public function getTransactionStatus(string $endUserId, string $correlator): array
{
    try {
        $response = $this->client->get(
            "/{$endUserId}/transactions/amount/{$correlator}"
        );
        return json_decode($response->getBody()->getContents(), true);
    } catch (RequestException $e) {
        return ['error' => $e->getMessage(), 'status' => $e->getResponse()?->getStatusCode()];
    }
}

// ── Usage ────────────────────────────────────────────────────
$status = $service->getTransactionStatus('263771234567', 'REF-001');
echo $status['transactionStatus']; // SUCCESS | FAILED | PENDING
```

#### 5 — Refund Transaction

```php
public function refundTransaction(array $data): array
{
    try {
        $response = $this->client->post('/transactions/refund/', [
            'json' => $data,
        ]);
        return json_decode($response->getBody()->getContents(), true);
    } catch (RequestException $e) {
        return ['error' => $e->getMessage(), 'status' => $e->getResponse()?->getStatusCode()];
    }
}

// ── Usage ────────────────────────────────────────────────────
$refund = $service->refundTransaction([
    'clientCorrelator'         => 'REFUND-001',
    'referenceCode'            => 'REF-INV-2024-001',
    'tranType'                 => 'MER',
    'endUserId'                => '263771234567',
    'originalEcocashReference' => 'MP240601.1200.T0123456',
    'paymentAmount'            => [
        'charginginformation' => [
            'amount'      => '5.00',
            'currency'    => 'ZWG',
            'description' => 'Refund',
        ],
        'chargeMetaData' => ['channel' => 'WEB'],
    ],
    'merchantCode'      => '287164',
    'merchantPin'       => '1234',
    'merchantNumber'    => '778503033',
    'countryCode'       => 'ZW',
    'terminalID'        => 'TERM001',
    'location'          => 'Harare',
    'superMerchantName' => 'EcoCash Sandbox',
    'merchantName'      => 'Test Merchant',
    'currencyCode'      => 'ZWG',
    'remarks'           => 'Refund',
]);
```

---

### Http Facade

> Laravel built-in · Fluent

#### 1 — Install

```bash
# No extra package — Http facade is built into Laravel

# .env
EIP_BASE_URL=https://developers.ecocash.co.zw/sandbox/payment/v1
EIP_USERNAME=your_username
EIP_PASSWORD=your_password
```

#### 2 — Client Setup

```php
<?php
// config/eip.php
return [
    'base_url' => env('EIP_BASE_URL',
        'https://developers.ecocash.co.zw/sandbox/payment/v1'),
    'username' => env('EIP_USERNAME'),
    'password' => env('EIP_PASSWORD'),
];

// ── app/Services/EcoCashEIPService.php ───────────────────────
namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Http\Client\PendingRequest;

class EcoCashEIPService
{
    private function client(): PendingRequest
    {
        return Http::baseUrl(config('eip.base_url'))
            ->withBasicAuth(config('eip.username'), config('eip.password'))
            ->acceptJson()
            ->contentType('application/json')
            ->timeout(30);
    }
}
```

#### 3 — Initiate Payment

```php
public function initiatePayment(array $data): array
{
    $response = $this->client()->post('/transactions/amount/', $data);

    if ($response->failed()) {
        return ['error' => $response->json('message'), 'status' => $response->status()];
    }

    return $response->json();
}

// ── Usage ────────────────────────────────────────────────────
$service = app(\App\Services\EcoCashEIPService::class);

$result = $service->initiatePayment([
    'clientCorrelator'           => 'REF-001',
    'notifyUrl'                  => 'https://yourapp.com/webhook/eip',
    'referenceCode'              => 'INV-2024-001',
    'tranType'                   => 'MER',
    'endUserId'                  => '263771234567',
    'remarks'                    => 'Online Payment',
    'transactionOperationStatus' => 'Charged',
    'paymentAmount'              => [
        'charginginformation' => [
            'amount'      => '5.00',
            'currency'    => 'ZWG',
            'description' => 'Online Payment',
        ],
        'chargeMetaData' => ['channel' => 'WEB'],
    ],
    'merchantCode'      => '287164',
    'merchantPin'       => '1234',
    'merchantNumber'    => '778503033',
    'countryCode'       => 'ZW',
    'terminalID'        => 'TERM001',
    'location'          => 'Harare',
    'superMerchantName' => 'EcoCash Sandbox',
    'merchantName'      => 'Test Merchant',
]);
```

#### 4 — Check Status

```php
public function getTransactionStatus(string $endUserId, string $correlator): array
{
    $response = $this->client()->get(
        "/{$endUserId}/transactions/amount/{$correlator}"
    );

    if ($response->failed()) {
        return ['error' => $response->json('message'), 'status' => $response->status()];
    }

    return $response->json();
}

// ── Usage ────────────────────────────────────────────────────
$status = $service->getTransactionStatus('263771234567', 'REF-001');
echo $status['transactionStatus']; // SUCCESS | FAILED | PENDING
```

#### 5 — Refund Transaction

```php
public function refundTransaction(array $data): array
{
    $response = $this->client()->post('/transactions/refund/', $data);

    if ($response->failed()) {
        return ['error' => $response->json('message'), 'status' => $response->status()];
    }

    return $response->json();
}

// ── Usage ────────────────────────────────────────────────────
$refund = $service->refundTransaction([
    'clientCorrelator'         => 'REFUND-001',
    'referenceCode'            => 'REF-INV-2024-001',
    'tranType'                 => 'MER',
    'endUserId'                => '263771234567',
    'originalEcocashReference' => 'MP240601.1200.T0123456',
    'paymentAmount'            => [
        'charginginformation' => [
            'amount'      => '5.00',
            'currency'    => 'ZWG',
            'description' => 'Refund',
        ],
        'chargeMetaData' => ['channel' => 'WEB'],
    ],
    'merchantCode'      => '287164',
    'merchantPin'       => '1234',
    'merchantNumber'    => '778503033',
    'countryCode'       => 'ZW',
    'terminalID'        => 'TERM001',
    'location'          => 'Harare',
    'superMerchantName' => 'EcoCash Sandbox',
    'merchantName'      => 'Test Merchant',
    'currencyCode'      => 'ZWG',
    'remarks'           => 'Refund',
]);
```

---

### Symfony Http

> PSR-18 · Framework-agnostic

#### 1 — Install

```bash
# Install via Composer (works in any PHP project — not Laravel-specific)
composer require symfony/http-client

# .env
EIP_BASE_URL=https://developers.ecocash.co.zw/sandbox/payment/v1
EIP_USERNAME=your_username
EIP_PASSWORD=your_password
```

#### 2 — Client Setup

```php
<?php
namespace App\Services;

use Symfony\Component\HttpClient\HttpClient;
use Symfony\Contracts\HttpClient\HttpClientInterface;

class EcoCashEIPService
{
    private HttpClientInterface $client;

    public function __construct()
    {
        $this->client = HttpClient::createWithOptions([
            'base_uri'   => $_ENV['EIP_BASE_URL'],
            'auth_basic' => [$_ENV['EIP_USERNAME'], $_ENV['EIP_PASSWORD']],
            'headers'    => [
                'Content-Type' => 'application/json',
                'Accept'       => 'application/json',
            ],
            'timeout'    => 30,
        ]);
    }
}
```

#### 3 — Initiate Payment

```php
public function initiatePayment(array $data): array
{
    $response = $this->client->request('POST', '/transactions/amount/', [
        'json' => $data,
    ]);

    return $response->toArray();
}

// ── Usage ────────────────────────────────────────────────────
$service = new EcoCashEIPService();

$result = $service->initiatePayment([
    'clientCorrelator'           => 'REF-001',
    'notifyUrl'                  => 'https://yourapp.com/webhook/eip',
    'referenceCode'              => 'INV-2024-001',
    'tranType'                   => 'MER',
    'endUserId'                  => '263771234567',
    'remarks'                    => 'Online Payment',
    'transactionOperationStatus' => 'Charged',
    'paymentAmount'              => [
        'charginginformation' => [
            'amount'      => '5.00',
            'currency'    => 'ZWG',
            'description' => 'Online Payment',
        ],
        'chargeMetaData' => ['channel' => 'WEB'],
    ],
    'merchantCode'      => '287164',
    'merchantPin'       => '1234',
    'merchantNumber'    => '778503033',
    'countryCode'       => 'ZW',
    'terminalID'        => 'TERM001',
    'location'          => 'Harare',
    'superMerchantName' => 'EcoCash Sandbox',
    'merchantName'      => 'Test Merchant',
]);
```

#### 4 — Check Status

```php
public function getTransactionStatus(string $endUserId, string $correlator): array
{
    $response = $this->client->request(
        'GET', "/{$endUserId}/transactions/amount/{$correlator}"
    );

    return $response->toArray();
}

// ── Usage ────────────────────────────────────────────────────
$status = $service->getTransactionStatus('263771234567', 'REF-001');
echo $status['transactionStatus']; // SUCCESS | FAILED | PENDING
```

#### 5 — Refund Transaction

```php
public function refundTransaction(array $data): array
{
    $response = $this->client->request('POST', '/transactions/refund/', [
        'json' => $data,
    ]);

    return $response->toArray();
}

// ── Usage ────────────────────────────────────────────────────
$refund = $service->refundTransaction([
    'clientCorrelator'         => 'REFUND-001',
    'referenceCode'            => 'REF-INV-2024-001',
    'tranType'                 => 'MER',
    'endUserId'                => '263771234567',
    'originalEcocashReference' => 'MP240601.1200.T0123456',
    'paymentAmount'            => [
        'charginginformation' => [
            'amount'      => '5.00',
            'currency'    => 'ZWG',
            'description' => 'Refund',
        ],
        'chargeMetaData' => ['channel' => 'WEB'],
    ],
    'merchantCode'      => '287164',
    'merchantPin'       => '1234',
    'merchantNumber'    => '778503033',
    'countryCode'       => 'ZW',
    'terminalID'        => 'TERM001',
    'location'          => 'Harare',
    'superMerchantName' => 'EcoCash Sandbox',
    'merchantName'      => 'Test Merchant',
    'currencyCode'      => 'ZWG',
    'remarks'           => 'Refund',
]);
```

---

## ⚡ JavaScript

**Section label:** HTTP CLIENT

| Variant | Portal subtitle | Notes |
|---|---|---|
| Axios | Promise-based · Universal | Response interceptor unwraps `res.data` |
| Fetch API | Native · Zero dependencies | Native in Node.js 18+ and modern browsers |
| Got | Node.js · Feature-rich | ESM-only; uses `prefixUrl`, so paths carry **no** leading slash |

Base URL: `https://developers.ecocash.co.zw/sandbox/payment/v1` · Auth: HTTP Basic Auth (Base64 `username:password`)

---

### Axios

> Promise-based · Universal

#### 1 — Install

```bash
# npm
npm install axios

# yarn / pnpm
yarn add axios

# .env (Node.js / Vite / Next.js)
EIP_BASE_URL=https://developers.ecocash.co.zw/sandbox/payment/v1
EIP_USERNAME=your_username
EIP_PASSWORD=your_password
```

#### 2 — Client Setup

```javascript
import axios from 'axios';

const BASE_URL = process.env.EIP_BASE_URL
  ?? 'https://developers.ecocash.co.zw/sandbox/payment/v1';

const credentials = btoa(
  `${process.env.EIP_USERNAME}:${process.env.EIP_PASSWORD}`
);

export const eipClient = axios.create({
  baseURL: BASE_URL,
  headers: { Authorization: `Basic ${credentials}`, 'Content-Type': 'application/json' },
  timeout: 30_000,
});

// Unwrap response data automatically
eipClient.interceptors.response.use(
  (res) => res.data,
  (err) => Promise.reject(err.response?.data ?? err.message),
);
```

#### 3 — Initiate Payment

```javascript
export async function initiatePayment(payload) {
  return eipClient.post('/transactions/amount/', payload);
}

// ── Usage ────────────────────────────────────────────────────
const result = await initiatePayment({
  clientCorrelator: 'REF-001',
  notifyUrl: 'https://yourapp.com/webhook/eip',
  referenceCode: 'INV-2024-001',
  tranType: 'MER',
  endUserId: '263771234567',
  remarks: 'Online Payment',
  transactionOperationStatus: 'Charged',
  paymentAmount: {
    charginginformation: {
      amount: '5.00',
      currency: 'ZWG',
      description: 'Online Payment',
    },
    chargeMetaData: { channel: 'WEB' },
  },
  merchantCode: '287164',
  merchantPin: '1234',
  merchantNumber: '778503033',
  countryCode: 'ZW',
  terminalID: 'TERM001',
  location: 'Harare',
  superMerchantName: 'EcoCash Sandbox',
  merchantName: 'Test Merchant',
});

console.log(result.transactionStatus); // PENDING
```

#### 4 — Check Status

```javascript
export async function getTransactionStatus(endUserId, clientCorrelator) {
  return eipClient.get(
    `/${endUserId}/transactions/amount/${clientCorrelator}`
  );
}

// ── Usage ────────────────────────────────────────────────────
const status = await getTransactionStatus('263771234567', 'REF-001');
console.log(status.transactionStatus); // SUCCESS | FAILED | PENDING
```

#### 5 — Refund Transaction

```javascript
export async function refundTransaction(payload) {
  return eipClient.post('/transactions/refund/', payload);
}

// ── Usage ────────────────────────────────────────────────────
const refund = await refundTransaction({
  clientCorrelator: 'REFUND-001',
  referenceCode: 'REF-INV-2024-001',
  tranType: 'MER',
  endUserId: '263771234567',
  originalEcocashReference: 'MP240601.1200.T0123456',
  paymentAmount: {
    charginginformation: {
      amount: '5.00',
      currency: 'ZWG',
      description: 'Refund',
    },
    chargeMetaData: { channel: 'WEB' },
  },
  merchantCode: '287164',
  merchantPin: '1234',
  merchantNumber: '778503033',
  countryCode: 'ZW',
  terminalID: 'TERM001',
  location: 'Harare',
  superMerchantName: 'EcoCash Sandbox',
  merchantName: 'Test Merchant',
  currencyCode: 'ZWG',
  remarks: 'Refund',
});

console.log(refund.transactionStatus); // SUCCESS
```

---

### Fetch API

> Native · Zero dependencies

#### 1 — Install

```bash
# No packages needed — Fetch is native in Node.js 18+ and all modern browsers

# .env (Node.js / Vite / Next.js)
EIP_BASE_URL=https://developers.ecocash.co.zw/sandbox/payment/v1
EIP_USERNAME=your_username
EIP_PASSWORD=your_password
```

#### 2 — Client Setup

```javascript
const BASE_URL = process.env.EIP_BASE_URL
  ?? 'https://developers.ecocash.co.zw/sandbox/payment/v1';

const credentials = btoa(
  `${process.env.EIP_USERNAME}:${process.env.EIP_PASSWORD}`
);

const BASE_HEADERS = {
  Authorization: `Basic ${credentials}`,
  'Content-Type': 'application/json',
  Accept: 'application/json',
};

async function eipFetch(path, init = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { ...BASE_HEADERS, ...init.headers },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`EIP ${res.status}: ${text}`);
  }
  return res.json();
}
```

#### 3 — Initiate Payment

```javascript
export async function initiatePayment(payload) {
  return eipFetch('/transactions/amount/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ── Usage ────────────────────────────────────────────────────
const result = await initiatePayment({
  clientCorrelator: 'REF-001',
  notifyUrl: 'https://yourapp.com/webhook/eip',
  referenceCode: 'INV-2024-001',
  tranType: 'MER',
  endUserId: '263771234567',
  remarks: 'Online Payment',
  transactionOperationStatus: 'Charged',
  paymentAmount: {
    charginginformation: {
      amount: '5.00',
      currency: 'ZWG',
      description: 'Online Payment',
    },
    chargeMetaData: { channel: 'WEB' },
  },
  merchantCode: '287164',
  merchantPin: '1234',
  merchantNumber: '778503033',
  countryCode: 'ZW',
  terminalID: 'TERM001',
  location: 'Harare',
  superMerchantName: 'EcoCash Sandbox',
  merchantName: 'Test Merchant',
});

console.log(result.transactionStatus); // PENDING
```

#### 4 — Check Status

```javascript
export async function getTransactionStatus(endUserId, clientCorrelator) {
  return eipFetch(
    `/${endUserId}/transactions/amount/${clientCorrelator}`
  );
}

// ── Usage ────────────────────────────────────────────────────
const status = await getTransactionStatus('263771234567', 'REF-001');
console.log(status.transactionStatus); // SUCCESS | FAILED | PENDING
```

#### 5 — Refund Transaction

```javascript
export async function refundTransaction(payload) {
  return eipFetch('/transactions/refund/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ── Usage ────────────────────────────────────────────────────
const refund = await refundTransaction({
  clientCorrelator: 'REFUND-001',
  referenceCode: 'REF-INV-2024-001',
  tranType: 'MER',
  endUserId: '263771234567',
  originalEcocashReference: 'MP240601.1200.T0123456',
  paymentAmount: {
    charginginformation: {
      amount: '5.00',
      currency: 'ZWG',
      description: 'Refund',
    },
    chargeMetaData: { channel: 'WEB' },
  },
  merchantCode: '287164',
  merchantPin: '1234',
  merchantNumber: '778503033',
  countryCode: 'ZW',
  terminalID: 'TERM001',
  location: 'Harare',
  superMerchantName: 'EcoCash Sandbox',
  merchantName: 'Test Merchant',
  currencyCode: 'ZWG',
  remarks: 'Refund',
});

console.log(refund.transactionStatus); // SUCCESS
```

---

### Got

> Node.js · Feature-rich

#### 1 — Install

```bash
# npm
npm install got

# yarn / pnpm
yarn add got   # ESM only — requires "type": "module" in package.json

# .env
EIP_BASE_URL=https://developers.ecocash.co.zw/sandbox/payment/v1
EIP_USERNAME=your_username
EIP_PASSWORD=your_password
```

#### 2 — Client Setup

```javascript
import got from 'got';

const credentials = Buffer.from(
  `${process.env.EIP_USERNAME}:${process.env.EIP_PASSWORD}`
).toString('base64');

export const eipClient = got.extend({
  prefixUrl: process.env.EIP_BASE_URL
    ?? 'https://developers.ecocash.co.zw/sandbox/payment/v1',
  headers: {
    Authorization: `Basic ${credentials}`,
    'Content-Type': 'application/json',
  },
  responseType: 'json',
  timeout: { request: 30_000 },
  retry: { limit: 2, methods: ['GET'] },
});
```

#### 3 — Initiate Payment

```javascript
export async function initiatePayment(payload) {
  const { body } = await eipClient.post('transactions/amount/', { json: payload });
  return body;
}

// ── Usage ────────────────────────────────────────────────────
const result = await initiatePayment({
  clientCorrelator: 'REF-001',
  notifyUrl: 'https://yourapp.com/webhook/eip',
  referenceCode: 'INV-2024-001',
  tranType: 'MER',
  endUserId: '263771234567',
  remarks: 'Online Payment',
  transactionOperationStatus: 'Charged',
  paymentAmount: {
    charginginformation: {
      amount: '5.00',
      currency: 'ZWG',
      description: 'Online Payment',
    },
    chargeMetaData: { channel: 'WEB' },
  },
  merchantCode: '287164',
  merchantPin: '1234',
  merchantNumber: '778503033',
  countryCode: 'ZW',
  terminalID: 'TERM001',
  location: 'Harare',
  superMerchantName: 'EcoCash Sandbox',
  merchantName: 'Test Merchant',
});

console.log(result.transactionStatus); // PENDING
```

#### 4 — Check Status

```javascript
export async function getTransactionStatus(endUserId, clientCorrelator) {
  const { body } = await eipClient.get(
    `${endUserId}/transactions/amount/${clientCorrelator}`
  );
  return body;
}

// ── Usage ────────────────────────────────────────────────────
const status = await getTransactionStatus('263771234567', 'REF-001');
console.log(status.transactionStatus); // SUCCESS | FAILED | PENDING
```

#### 5 — Refund Transaction

```javascript
export async function refundTransaction(payload) {
  const { body } = await eipClient.post('transactions/refund/', { json: payload });
  return body;
}

// ── Usage ────────────────────────────────────────────────────
const refund = await refundTransaction({
  clientCorrelator: 'REFUND-001',
  referenceCode: 'REF-INV-2024-001',
  tranType: 'MER',
  endUserId: '263771234567',
  originalEcocashReference: 'MP240601.1200.T0123456',
  paymentAmount: {
    charginginformation: {
      amount: '5.00',
      currency: 'ZWG',
      description: 'Refund',
    },
    chargeMetaData: { channel: 'WEB' },
  },
  merchantCode: '287164',
  merchantPin: '1234',
  merchantNumber: '778503033',
  countryCode: 'ZW',
  terminalID: 'TERM001',
  location: 'Harare',
  superMerchantName: 'EcoCash Sandbox',
  merchantName: 'Test Merchant',
  currencyCode: 'ZWG',
  remarks: 'Refund',
});

console.log(refund.transactionStatus); // SUCCESS
```

---

## ⬡ C#

Portal groups these under the heading **.NET CLIENT**.

| Variant | Portal subtitle | Notes |
|---|---|---|
| HttpClient | .NET built-in · Flexible | Returns `JsonDocument`; no DTOs required |
| RestSharp | NuGet · Simple REST client | Deserialises into `TransactionResponse` |
| Refit | .NET · Declarative interface | Interface-driven; DI registration via `Refit.HttpClientFactory` |

Base URL: `https://developers.ecocash.co.zw/sandbox/payment/v1` · Auth: HTTP Basic Auth (Base64 `username:password`)

---

### HttpClient

> .NET built-in · Flexible

#### 1 — Install

```bash
# HttpClient is built into .NET — no extra packages needed
dotnet new console -n EcoCashEIP
```

```json
# appsettings.json
{
  "EIP": {
    "BaseUrl": "https://developers.ecocash.co.zw/sandbox/payment/v1",
    "Username": "your_username",
    "Password": "your_password"
  }
}
```

#### 2 — Client Setup

```csharp
using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

public sealed class EcoCashEIPClient : IDisposable
{
    private const string BaseUrl =
        "https://developers.ecocash.co.zw/sandbox/payment/v1";

    private readonly HttpClient _http;

    public EcoCashEIPClient(string username, string password)
    {
        _http = new HttpClient { BaseAddress = new Uri(BaseUrl) };

        var token = Convert.ToBase64String(
            Encoding.UTF8.GetBytes($"{username}:{password}"));

        _http.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Basic", token);
        _http.DefaultRequestHeaders.Accept
            .Add(new MediaTypeWithQualityHeaderValue("application/json"));
        _http.Timeout = TimeSpan.FromSeconds(30);
    }

    public void Dispose() => _http.Dispose();
}
```

#### 3 — Initiate Payment

```csharp
public async Task<JsonDocument> InitiatePaymentAsync(object payload)
{
    var json = JsonSerializer.Serialize(payload);
    var content = new StringContent(json, Encoding.UTF8, "application/json");

    var response = await _http.PostAsync("/transactions/amount/", content);
    response.EnsureSuccessStatusCode();

    return JsonDocument.Parse(await response.Content.ReadAsStringAsync());
}

// ── Usage ────────────────────────────────────────────────────
await using var client = new EcoCashEIPClient("YOUR_USERNAME", "YOUR_PASSWORD");

var result = await client.InitiatePaymentAsync(new {
    clientCorrelator = "REF-001",
    notifyUrl = "https://yourapp.com/webhook/eip",
    referenceCode = "INV-2024-001",
    tranType = "MER",
    endUserId = "263771234567",
    remarks = "Online Payment",
    transactionOperationStatus = "Charged",
    paymentAmount = new {
        charginginformation = new {
            amount = "5.00",
            currency = "ZWG",
            description = "Online Payment",
        },
        chargeMetaData = new { channel = "WEB" },
    },
    merchantCode = "287164",
    merchantPin = "1234",
    merchantNumber = "778503033",
    countryCode = "ZW",
    terminalID = "TERM001",
    location = "Harare",
    superMerchantName = "EcoCash Sandbox",
    merchantName = "Test Merchant",
});

Console.WriteLine(result.RootElement.GetProperty("transactionStatus").GetString());
```

> **Verbatim note.** The portal writes `await using var client = new EcoCashEIPClient(...)`, but the class in step 2 implements `IDisposable`, not `IAsyncDisposable`. As published this will not compile — use `using var`, or add `IAsyncDisposable`. Reproduced unchanged above; see cross-cutting note 8.

#### 4 — Check Status

```csharp
public async Task<JsonDocument> GetTransactionStatusAsync(
    string endUserId, string clientCorrelator)
{
    var response = await _http.GetAsync(
        $"/{endUserId}/transactions/amount/{clientCorrelator}");
    response.EnsureSuccessStatusCode();
    return JsonDocument.Parse(await response.Content.ReadAsStringAsync());
}

// ── Usage ────────────────────────────────────────────────────
var status = await client.GetTransactionStatusAsync("263771234567", "REF-001");
Console.WriteLine(status.RootElement.GetProperty("transactionStatus").GetString());
```

#### 5 — Refund Transaction

```csharp
public async Task<JsonDocument> RefundTransactionAsync(object payload)
{
    var json = JsonSerializer.Serialize(payload);
    var content = new StringContent(json, Encoding.UTF8, "application/json");

    var response = await _http.PostAsync("/transactions/refund/", content);
    response.EnsureSuccessStatusCode();

    return JsonDocument.Parse(await response.Content.ReadAsStringAsync());
}

// ── Usage ────────────────────────────────────────────────────
var refund = await client.RefundTransactionAsync(new {
    clientCorrelator = "REFUND-001",
    referenceCode = "REF-INV-2024-001",
    tranType = "MER",
    endUserId = "263771234567",
    originalEcocashReference = "MP240601.1200.T0123456",
    paymentAmount = new {
        charginginformation = new {
            amount = "5.00",
            currency = "ZWG",
            description = "Refund",
        },
        chargeMetaData = new { channel = "WEB" },
    },
    merchantCode = "287164",
    merchantPin = "1234",
    merchantNumber = "778503033",
    countryCode = "ZW",
    terminalID = "TERM001",
    location = "Harare",
    superMerchantName = "EcoCash Sandbox",
    merchantName = "Test Merchant",
    currencyCode = "ZWG",
    remarks = "Refund",
});
```

---

### RestSharp

> NuGet · Simple REST client

#### 1 — Install

```bash
# .NET CLI
dotnet add package RestSharp
```

```json
# appsettings.json
{
  "EIP": {
    "BaseUrl": "https://developers.ecocash.co.zw/sandbox/payment/v1",
    "Username": "your_username",
    "Password": "your_password"
  }
}
```

#### 2 — Client Setup

```csharp
using RestSharp;
using RestSharp.Authenticators;
using System;
using System.Threading.Tasks;

public sealed class EcoCashEIPClient : IDisposable
{
    private readonly RestClient _client;

    public EcoCashEIPClient(string username, string password)
    {
        var options = new RestClientOptions(
            "https://developers.ecocash.co.zw/sandbox/payment/v1")
        {
            Authenticator = new HttpBasicAuthenticator(username, password),
            MaxTimeout = 30_000,
        };
        _client = new RestClient(options);
    }

    public void Dispose() => _client.Dispose();
}
```

#### 3 — Initiate Payment

```csharp
public async Task<TransactionResponse> InitiatePaymentAsync(object payload)
{
    var request = new RestRequest("/transactions/amount/", Method.Post);
    request.AddJsonBody(payload);

    var response = await _client.ExecuteAsync<TransactionResponse>(request);
    if (!response.IsSuccessful)
        throw new Exception($"EIP error: HTTP {(int)response.StatusCode}");

    return response.Data!;
}

// ── Usage ────────────────────────────────────────────────────
using var client = new EcoCashEIPClient("YOUR_USERNAME", "YOUR_PASSWORD");

var result = await client.InitiatePaymentAsync(new {
    clientCorrelator = "REF-001",
    notifyUrl = "https://yourapp.com/webhook/eip",
    referenceCode = "INV-2024-001",
    tranType = "MER",
    endUserId = "263771234567",
    remarks = "Online Payment",
    transactionOperationStatus = "Charged",
    paymentAmount = new {
        charginginformation = new {
            amount = "5.00",
            currency = "ZWG",
            description = "Online Payment",
        },
        chargeMetaData = new { channel = "WEB" },
    },
    merchantCode = "287164",
    merchantPin = "1234",
    merchantNumber = "778503033",
    countryCode = "ZW",
    terminalID = "TERM001",
    location = "Harare",
    superMerchantName = "EcoCash Sandbox",
    merchantName = "Test Merchant",
});

Console.WriteLine(result.TransactionStatus); // PENDING
```

#### 4 — Check Status

```csharp
public async Task<TransactionResponse> GetTransactionStatusAsync(
    string endUserId, string clientCorrelator)
{
    var request = new RestRequest(
        $"/{endUserId}/transactions/amount/{clientCorrelator}", Method.Get);
    var response = await _client.ExecuteAsync<TransactionResponse>(request);

    if (!response.IsSuccessful)
        throw new Exception($"EIP error: HTTP {(int)response.StatusCode}");

    return response.Data!;
}

// ── Usage ────────────────────────────────────────────────────
var status = await client.GetTransactionStatusAsync("263771234567", "REF-001");
Console.WriteLine(status.TransactionStatus); // SUCCESS | FAILED | PENDING
```

#### 5 — Refund Transaction

```csharp
public async Task<TransactionResponse> RefundTransactionAsync(object payload)
{
    var request = new RestRequest("/transactions/refund/", Method.Post);
    request.AddJsonBody(payload);

    var response = await _client.ExecuteAsync<TransactionResponse>(request);
    if (!response.IsSuccessful)
        throw new Exception($"EIP error: HTTP {(int)response.StatusCode}");

    return response.Data!;
}

// ── Usage ────────────────────────────────────────────────────
var refund = await client.RefundTransactionAsync(new {
    clientCorrelator = "REFUND-001",
    referenceCode = "REF-INV-2024-001",
    tranType = "MER",
    endUserId = "263771234567",
    originalEcocashReference = "MP240601.1200.T0123456",
    paymentAmount = new {
        charginginformation = new {
            amount = "5.00",
            currency = "ZWG",
            description = "Refund",
        },
        chargeMetaData = new { channel = "WEB" },
    },
    merchantCode = "287164",
    merchantPin = "1234",
    merchantNumber = "778503033",
    countryCode = "ZW",
    terminalID = "TERM001",
    location = "Harare",
    superMerchantName = "EcoCash Sandbox",
    merchantName = "Test Merchant",
    currencyCode = "ZWG",
    remarks = "Refund",
});
```

---

### Refit

> .NET · Declarative interface

#### 1 — Install

```bash
# .NET CLI
dotnet add package Refit
dotnet add package Refit.HttpClientFactory   # for ASP.NET Core DI
```

```json
# appsettings.json
{
  "EIP": {
    "BaseUrl": "https://developers.ecocash.co.zw/sandbox/payment/v1",
    "Username": "your_username",
    "Password": "your_password"
  }
}
```

#### 2 — Client Setup

```csharp
using Refit;
using System.Threading.Tasks;

// 1. Declare the interface — Refit generates the implementation
public interface IEIPApi
{
    [Post("/transactions/amount/")]
    Task<TransactionResponse> InitiatePaymentAsync([Body] PaymentRequest request);

    [Get("/{endUserId}/transactions/amount/{clientCorrelator}")]
    Task<TransactionResponse> GetTransactionStatusAsync(
        string endUserId, string clientCorrelator);

    [Post("/transactions/refund/")]
    Task<TransactionResponse> RefundTransactionAsync([Body] RefundRequest request);
}

// 2. Register in Program.cs (ASP.NET Core)
builder.Services
    .AddRefitClient<IEIPApi>(new RefitSettings
    {
        AuthorizationHeaderValueGetter = (_, __) =>
        {
            var token = Convert.ToBase64String(
                Encoding.UTF8.GetBytes($"{username}:{password}"));
            return Task.FromResult(token);
        },
    })
    .ConfigureHttpClient(c =>
    {
        c.BaseAddress = new Uri(builder.Configuration["EIP:BaseUrl"]!);
        c.Timeout = TimeSpan.FromSeconds(30);
    });
```

> **Verbatim note.** Three things in this snippet need attention before it will run: `username` / `password` are referenced but never declared; `Convert` and `Encoding` need `using System;` and `using System.Text;`; and `AuthorizationHeaderValueGetter` supplies only the *token*, so the scheme must be declared separately — Refit defaults to `Bearer`. For HTTP Basic you must add `[Headers("Authorization: Basic")]` on the interface. Reproduced unchanged; see cross-cutting note 8.

#### 3 — Initiate Payment

```csharp
public class PaymentService(IEIPApi eipApi)
{
    public Task<TransactionResponse> PayAsync(string endUserId) =>
        eipApi.InitiatePaymentAsync(new PaymentRequest
        {
            ClientCorrelator = $"REF-{DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()}",
            NotifyUrl = "https://yourapp.com/webhook/eip",
            ReferenceCode = "INV-2024-001",
            TranType = "MER",
            EndUserId = endUserId,
            Remarks = "Online Payment",
            TransactionOperationStatus = "Charged",
            PaymentAmount = new PaymentAmount
            {
                Charginginformation = new ChargingInfo
                {
                    Amount = "5.00",
                    Currency = "ZWG",
                    Description = "Online Payment",
                },
                ChargeMetaData = new ChargeMetaData { Channel = "WEB" },
            },
            MerchantCode = "287164",
            MerchantPin = "1234",
            MerchantNumber = "778503033",
            CountryCode = "ZW",
            TerminalID = "TERM001",
            Location = "Harare",
            SuperMerchantName = "EcoCash Sandbox",
            MerchantName = "Test Merchant",
        });
}
```

#### 4 — Check Status

```csharp
public Task<TransactionResponse> GetStatusAsync(
    string endUserId, string correlator) =>
    eipApi.GetTransactionStatusAsync(endUserId, correlator);

// ── Usage ────────────────────────────────────────────────────
var status = await paymentService.GetStatusAsync("263771234567", "REF-001");
Console.WriteLine(status.TransactionStatus); // SUCCESS | FAILED | PENDING
```

#### 5 — Refund Transaction

```csharp
public Task<TransactionResponse> RefundAsync(
    string endUserId, string ecocashRef) =>
    eipApi.RefundTransactionAsync(new RefundRequest
    {
        ClientCorrelator = $"REFUND-{DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()}",
        ReferenceCode = "REF-INV-2024-001",
        TranType = "MER",
        EndUserId = endUserId,
        OriginalEcocashReference = ecocashRef,
        PaymentAmount = new PaymentAmount
        {
            Charginginformation = new ChargingInfo
            {
                Amount = "5.00",
                Currency = "ZWG",
                Description = "Refund",
            },
            ChargeMetaData = new ChargeMetaData { Channel = "WEB" },
        },
        MerchantCode = "287164",
        MerchantPin = "1234",
        MerchantNumber = "778503033",
        CountryCode = "ZW",
        TerminalID = "TERM001",
        Location = "Harare",
        SuperMerchantName = "EcoCash Sandbox",
        MerchantName = "Test Merchant",
        CurrencyCode = "ZWG",
        Remarks = "Refund",
    });

// ── Usage ────────────────────────────────────────────────────
var refund = await paymentService.RefundAsync(
    "263771234567", "MP240601.1200.T0123456");
```

---

## 🐍 Python

**Section label:** HTTP CLIENT

| Variant | Portal subtitle | Notes |
|---|---|---|
| Requests | Sync · Most popular | Wraps a `requests.Session` in an `EIPClient` class |
| HTTPX | Sync/Async · Modern | Module-level `httpx.Client`; async swap documented inline |
| aiohttp | Async · High performance | New `ClientSession` per call via `make_session()` |

Base URL: `https://developers.ecocash.co.zw/sandbox/payment/v1` · Auth: HTTP Basic Auth (Base64 `username:password`)

> **Important divergence.** All three Python variants read **`transactionOperationStatus`** from the response, whereas the Java, PHP, JavaScript and C# variants read **`transactionStatus`**. See cross-cutting note 2 before copying.

---

### Requests

> Sync · Most popular

#### 1 — Install

```bash
pip install requests python-dotenv

# requirements.txt
requests>=2.32.3
python-dotenv>=1.0.0

# .env
EIP_BASE_URL=https://developers.ecocash.co.zw/sandbox/payment/v1
EIP_USERNAME=your_username
EIP_PASSWORD=your_password
```

#### 2 — Client Setup

```python
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

class EIPClient:
    def __init__(self):
        self.base_url = os.environ["EIP_BASE_URL"]
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(
            os.environ["EIP_USERNAME"],
            os.environ["EIP_PASSWORD"],
        )
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _url(self, path: str) -> str:
        return self.base_url.rstrip("/") + path

client = EIPClient()
```

#### 3 — Initiate Payment

```python
def initiate_payment(self, payload: dict) -> dict:
    resp = self.session.post(self._url("/transactions/amount/"), json=payload)
    resp.raise_for_status()
    return resp.json()

# ── Usage ────────────────────────────────────────────────────
tx = client.initiate_payment({
    "clientCorrelator": "REF-001",
    "notifyUrl": "https://yourapp.com/webhook/eip",
    "referenceCode": "INV-2024-001",
    "tranType": "MER",
    "endUserId": "263771234567",
    "remarks": "Online Payment",
    "transactionOperationStatus": "Charged",
    "paymentAmount": {
        "charginginformation": {
            "amount": "5.00",
            "currency": "ZWG",
            "description": "Online Payment",
        },
        "chargeMetaData": {"channel": "WEB"},
    },
    "merchantCode": "287164",
    "merchantPin": "1234",
    "merchantNumber": "778503033",
    "countryCode": "ZW",
    "terminalID": "TERM001",
    "location": "Harare",
    "superMerchantName": "EcoCash Sandbox",
    "merchantName": "Test Merchant",
})
print(tx["transactionOperationStatus"])  # Charged | Failed | Pending
```

> **Verbatim note.** Steps 3–5 are published as bare `def ...(self, ...)` blocks. They are methods of `EIPClient` from step 2 and must be indented into that class body; the trailing `# ── Usage ──` lines are module-level and call them through the `client` instance.

#### 4 — Check Status

```python
def get_transaction_status(
    self, end_user_id: str, client_correlator: str
) -> dict:
    resp = self.session.get(
        self._url(f"/{end_user_id}/transactions/amount/{client_correlator}")
    )
    resp.raise_for_status()
    return resp.json()

# ── Usage ────────────────────────────────────────────────────
status = client.get_transaction_status("263771234567", "REF-001")
print(status["transactionOperationStatus"])  # SUCCESS | FAILED | PENDING
```

#### 5 — Refund Transaction

```python
def refund_transaction(self, payload: dict) -> dict:
    resp = self.session.post(self._url("/transactions/refund/"), json=payload)
    resp.raise_for_status()
    return resp.json()

# ── Usage ────────────────────────────────────────────────────
refund = client.refund_transaction({
    "clientCorrelator": "REFUND-001",
    "referenceCode": "REF-INV-2024-001",
    "tranType": "MER",
    "endUserId": "263771234567",
    "originalEcocashReference": "MP240601.1200.T0123456",
    "paymentAmount": {
        "charginginformation": {
            "amount": "5.00",
            "currency": "ZWG",
            "description": "Refund",
        },
        "chargeMetaData": {"channel": "WEB"},
    },
    "merchantCode": "287164",
    "merchantPin": "1234",
    "merchantNumber": "778503033",
    "countryCode": "ZW",
    "terminalID": "TERM001",
    "location": "Harare",
    "superMerchantName": "EcoCash Sandbox",
    "merchantName": "Test Merchant",
    "currencyCode": "ZWG",
    "remarks": "Refund",
})
```

---

### HTTPX

> Sync/Async · Modern

#### 1 — Install

```bash
pip install httpx python-dotenv

# requirements.txt
httpx>=0.27.0
python-dotenv>=1.0.0

# .env
EIP_BASE_URL=https://developers.ecocash.co.zw/sandbox/payment/v1
EIP_USERNAME=your_username
EIP_PASSWORD=your_password
```

#### 2 — Client Setup

```python
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

client = httpx.Client(
    base_url=os.environ["EIP_BASE_URL"],
    auth=(os.environ["EIP_USERNAME"], os.environ["EIP_PASSWORD"]),
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
    },
    timeout=30.0,
)

# For async usage, swap httpx.Client → httpx.AsyncClient
# async_client = httpx.AsyncClient(base_url=..., auth=..., headers=...)
```

#### 3 — Initiate Payment

```python
def initiate_payment(payload: dict) -> dict:
    resp = client.post("/transactions/amount/", json=payload)
    resp.raise_for_status()
    return resp.json()

# ── Usage ────────────────────────────────────────────────────
tx = initiate_payment({
    "clientCorrelator": "REF-001",
    "notifyUrl": "https://yourapp.com/webhook/eip",
    "referenceCode": "INV-2024-001",
    "tranType": "MER",
    "endUserId": "263771234567",
    "remarks": "Online Payment",
    "transactionOperationStatus": "Charged",
    "paymentAmount": {
        "charginginformation": {
            "amount": "5.00",
            "currency": "ZWG",
            "description": "Online Payment",
        },
        "chargeMetaData": {"channel": "WEB"},
    },
    "merchantCode": "287164",
    "merchantPin": "1234",
    "merchantNumber": "778503033",
    "countryCode": "ZW",
    "terminalID": "TERM001",
    "location": "Harare",
    "superMerchantName": "EcoCash Sandbox",
    "merchantName": "Test Merchant",
})
print(tx["transactionOperationStatus"])  # Charged | Failed | Pending
```

#### 4 — Check Status

```python
def get_transaction_status(
    end_user_id: str, client_correlator: str
) -> dict:
    resp = client.get(
        f"/{end_user_id}/transactions/amount/{client_correlator}"
    )
    resp.raise_for_status()
    return resp.json()

# ── Usage ────────────────────────────────────────────────────
status = get_transaction_status("263771234567", "REF-001")
print(status["transactionOperationStatus"])  # SUCCESS | FAILED | PENDING
```

#### 5 — Refund Transaction

```python
def refund_transaction(payload: dict) -> dict:
    resp = client.post("/transactions/refund/", json=payload)
    resp.raise_for_status()
    return resp.json()

# ── Usage ────────────────────────────────────────────────────
refund = refund_transaction({
    "clientCorrelator": "REFUND-001",
    "referenceCode": "REF-INV-2024-001",
    "tranType": "MER",
    "endUserId": "263771234567",
    "originalEcocashReference": "MP240601.1200.T0123456",
    "paymentAmount": {
        "charginginformation": {
            "amount": "5.00",
            "currency": "ZWG",
            "description": "Refund",
        },
        "chargeMetaData": {"channel": "WEB"},
    },
    "merchantCode": "287164",
    "merchantPin": "1234",
    "merchantNumber": "778503033",
    "countryCode": "ZW",
    "terminalID": "TERM001",
    "location": "Harare",
    "superMerchantName": "EcoCash Sandbox",
    "merchantName": "Test Merchant",
    "currencyCode": "ZWG",
    "remarks": "Refund",
})
```

---

### aiohttp

> Async · High performance

#### 1 — Install

```bash
pip install aiohttp python-dotenv

# requirements.txt
aiohttp>=3.10.0
python-dotenv>=1.0.0

# .env
EIP_BASE_URL=https://developers.ecocash.co.zw/sandbox/payment/v1
EIP_USERNAME=your_username
EIP_PASSWORD=your_password
```

#### 2 — Client Setup

```python
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

EIP_BASE_URL = os.environ["EIP_BASE_URL"]
EIP_AUTH = aiohttp.BasicAuth(
    os.environ["EIP_USERNAME"],
    os.environ["EIP_PASSWORD"],
)
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

def make_session() -> aiohttp.ClientSession:
    return aiohttp.ClientSession(
        base_url=EIP_BASE_URL,
        auth=EIP_AUTH,
        headers=HEADERS,
    )
```

> **Verbatim note.** Older aiohttp releases accept an **origin only** (scheme + host + optional port) in `ClientSession(base_url=...)` and reject a base URL that carries a path. Newer releases accept a base path, but only when it ends in `/` and the request path has **no** leading slash. The sample does neither: its base URL has the path `/sandbox/payment/v1` with no trailing slash, and steps 3–5 use leading-slash paths. So `/sandbox/payment/v1` is lost (or the session is refused) on every aiohttp version. See cross-cutting note 5.

#### 3 — Initiate Payment

```python
async def initiate_payment(payload: dict) -> dict:
    async with make_session() as session:
        async with session.post(
            "/transactions/amount/", json=payload
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

# ── Usage ────────────────────────────────────────────────────
tx = asyncio.run(initiate_payment({
    "clientCorrelator": "REF-001",
    "notifyUrl": "https://yourapp.com/webhook/eip",
    "referenceCode": "INV-2024-001",
    "tranType": "MER",
    "endUserId": "263771234567",
    "remarks": "Online Payment",
    "transactionOperationStatus": "Charged",
    "paymentAmount": {
        "charginginformation": {
            "amount": "5.00",
            "currency": "ZWG",
            "description": "Online Payment",
        },
        "chargeMetaData": {"channel": "WEB"},
    },
    "merchantCode": "287164",
    "merchantPin": "1234",
    "merchantNumber": "778503033",
    "countryCode": "ZW",
    "terminalID": "TERM001",
    "location": "Harare",
    "superMerchantName": "EcoCash Sandbox",
    "merchantName": "Test Merchant",
}))
print(tx["transactionOperationStatus"])  # Charged | Failed | Pending
```

#### 4 — Check Status

```python
async def get_transaction_status(
    end_user_id: str, client_correlator: str
) -> dict:
    async with make_session() as session:
        async with session.get(
            f"/{end_user_id}/transactions/amount/{client_correlator}"
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

# ── Usage ────────────────────────────────────────────────────
status = asyncio.run(
    get_transaction_status("263771234567", "REF-001")
)
print(status["transactionOperationStatus"])  # SUCCESS | FAILED | PENDING
```

#### 5 — Refund Transaction

```python
async def refund_transaction(payload: dict) -> dict:
    async with make_session() as session:
        async with session.post(
            "/transactions/refund/", json=payload
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

# ── Usage ────────────────────────────────────────────────────
refund = asyncio.run(refund_transaction({
    "clientCorrelator": "REFUND-001",
    "referenceCode": "REF-INV-2024-001",
    "tranType": "MER",
    "endUserId": "263771234567",
    "originalEcocashReference": "MP240601.1200.T0123456",
    "paymentAmount": {
        "charginginformation": {
            "amount": "5.00",
            "currency": "ZWG",
            "description": "Refund",
        },
        "chargeMetaData": {"channel": "WEB"},
    },
    "merchantCode": "287164",
    "merchantPin": "1234",
    "merchantNumber": "778503033",
    "countryCode": "ZW",
    "terminalID": "TERM001",
    "location": "Harare",
    "superMerchantName": "EcoCash Sandbox",
    "merchantName": "Test Merchant",
    "currencyCode": "ZWG",
    "remarks": "Refund",
}))
```

---

## Cross-cutting notes and corrections

Everything above is a verbatim reproduction of the portal's SDKs & Codegen tab. Everything in this section is **review commentary**, clearly separated so it can never be mistaken for portal content. Each note compares the tab's samples **with each other** only.

### Note 1 — Refund payload shape is identical across all 15 variants

Checked in all fifteen refund samples (Java ×3, PHP ×3, JavaScript ×3, C# ×3, Python ×3):

| Observation | Count | Comment |
|---|---|---|
| `tranType` set to `"MER"` | 15 / 15 | The same value the payment samples use. The SDK tab does not list the valid `tranType` values or say whether refunds need a different one. |
| `originalEcocashReference` present | 15 / 15 | The only field that links a refund to its original payment (example value `MP240601.1200.T0123456`). |
| `currencyCode` present at top level | 15 / 15 | Duplicates `paymentAmount.charginginformation.currency` (both `"ZWG"`). It never appears in the payment samples. |
| `remarks` present | 15 / 15 | Set to `"Refund"`. |
| `notifyUrl` present | 0 / 15 | Refund samples never carry a callback URL, unlike the payment samples. |
| `transactionOperationStatus` present | 0 / 15 | Present in all 15 *payment* samples (`"Charged"`), absent from all 15 refund samples. |

**Recommendation.** Copy the refund shape as published, but keep `tranType` and `currencyCode` configurable. The SDK tab doesn't explain either, so confirm them before production.

### Note 2 — Two different names for the transaction status field

| Variants | Field read | Count |
|---|---|---|
| Java, PHP, JavaScript, C# | `transactionStatus` / `TransactionStatus` | 12 of 15 |
| Python (Requests, HTTPX, aiohttp) | `transactionOperationStatus` | 3 of 15 |

`transactionOperationStatus` is also a **request** field in every payment sample, where it carries the value `"Charged"`. Using the same name for a request instruction and a response outcome is the single most likely source of integration bugs in this SDK set.

The Python comments are internally inconsistent too: step 3 annotates the value as `# Charged | Failed | Pending`, while step 4 annotates the same key as `# SUCCESS | FAILED | PENDING`. The other languages annotate `# SUCCESS | FAILED | PENDING` for status and `PENDING` after a payment.

Parse defensively until the canonical name is confirmed:

```python
def read_status(body: dict) -> str | None:
    for key in ("transactionStatus", "transactionOperationStatus"):
        if key in body:
            return body[key]
    return None
```

```javascript
const readStatus = (body) =>
  body.transactionStatus ?? body.transactionOperationStatus ?? null;
```

### Note 3 — Sandbox values used in every sample

All 15 variants use the same fixture values:

| Field | Value |
|---|---|
| `merchantCode` | `287164` |
| `merchantPin` | `1234` |
| `merchantNumber` | `778503033` |
| `countryCode` | `ZW` |
| `terminalID` | `TERM001` |
| `location` | `Harare` |
| `superMerchantName` | `EcoCash Sandbox` |
| `merchantName` | `Test Merchant` |
| `channel` | `WEB` |
| `currency` | `ZWG` |
| `amount` | `"5.00"` (JSON string) |
| `endUserId` | `263771234567` |
| `notifyUrl` (payments) | `https://yourapp.com/webhook/eip` |
| `referenceCode` | `INV-2024-001` (payment), `REF-INV-2024-001` (refund) |

Credentials come from `EIP_USERNAME` / `EIP_PASSWORD` (or `appsettings.json` → `EIP:Username` / `EIP:Password` in C#). The SDK tab does not say whether the merchant values above are live sandbox fixtures or placeholders. Treat them as syntax illustrations until confirmed.

### Note 4 — `amount` is sent as a string

Every sample sends `amount` as a **string** (`"5.00"`), including the typed C# Refit sample (`Amount = "5.00"`). The SDK tab doesn't state the field's type or allowed precision. Follow the samples (a two-decimal string), and keep the serialisation in one place so it can be switched if needed.

### Note 5 — Base-URL joining differs by client, and some variants will drop `/sandbox/payment/v1`

The base URL contains a path segment (`/sandbox/payment/v1`). How a client joins that base with a relative path is library-specific, and several samples combine a path-bearing base with a **leading-slash** relative path — a combination that discards the base path under RFC 3986 resolution.

| Variant | Base mechanism | Path in sample | Risk |
|---|---|---|---|
| Java WebClient / RestClient | `baseUrl(...)` | `/transactions/amount/` | Low — Spring appends rather than resolves |
| Java Feign | `url = ...` | `/transactions/amount/` | Low |
| PHP Guzzle | `base_uri` | `/transactions/amount/` | **High** — Guzzle uses RFC 3986 resolution; a leading slash replaces the base path |
| PHP Http Facade | `Http::baseUrl(...)` | `/transactions/amount/` | Low — Laravel concatenates and normalises the slash |
| PHP Symfony Http | `base_uri` | `/transactions/amount/` | **High** — same RFC 3986 resolution as Guzzle |
| JS Axios | `baseURL` | `/transactions/amount/` | Low — Axios concatenates |
| JS Fetch | template string | `/transactions/amount/` | Low — plain concatenation |
| JS Got | `prefixUrl` | `transactions/amount/` (no leading slash) | Low — and Got **throws** if you add a leading slash |
| C# HttpClient | `BaseAddress` | `/transactions/amount/` | **High** — a leading slash discards the base path |
| C# RestSharp | `RestClientOptions(base)` | `/transactions/amount/` | Medium — verify against your RestSharp version |
| C# Refit | `BaseAddress` via `ConfigureHttpClient` | `/transactions/amount/` | Low — Refit prepends `BaseAddress.AbsolutePath` to every route (routes must start with `/`), so `/sandbox/payment/v1` is kept |
| Python Requests | manual `rstrip("/") + path` | `/transactions/amount/` | Low — explicit concatenation |
| Python HTTPX | `base_url` | `/transactions/amount/` | Low — HTTPX merges base path with the relative path |
| Python aiohttp | `ClientSession(base_url=...)` | `/transactions/amount/` | **High** — older versions reject a base URL with a path. Newer versions keep it only with a trailing slash on the base and no leading slash on the path; the sample has neither |

**Recommendation.** Log the fully resolved request URL once at start-up in every environment. The first integration test should assert that the outgoing URL is `https://developers.ecocash.co.zw/sandbox/payment/v1/transactions/amount/`.

### Note 6 — Trailing slashes are significant

`/transactions/amount/` and `/transactions/refund/` are published **with** a trailing slash in every sample and in the Key Endpoints panel. Do not normalise them away; some gateways treat `/transactions/amount` as a distinct, unrouted path.

The status endpoint has no trailing slash: `/{endUserId}/transactions/amount/{clientCorrelator}`.

### Note 7 — `btoa` in the Axios and Fetch samples

Both samples build the Basic credential with `btoa(...)`. Two caveats:

- `btoa` is a browser API. It exists in Node.js 16+ as a deprecated global, so the samples will run, but `Buffer.from(...).toString('base64')` — as used in the Got sample — is the correct Node.js form and handles non-Latin-1 characters safely.
- Both samples read `process.env.EIP_USERNAME` / `EIP_PASSWORD`. If this code is bundled for the browser, the bundler will inline those values into the shipped JavaScript. **Never ship EIP credentials to a browser bundle** — call the EIP API from your own server and expose only a narrow endpoint to the front end.

### Note 8 — Types referenced but never published

Several samples reference types that the SDKs & Codegen tab never defines:

`PaymentRequest`, `RefundRequest`, `PaymentAmount`, `ChargingInfo`, `ChargeMetaData`, `TransactionResponse`

You must author these yourself. Two practical consequences for C#:

- The Refit and RestSharp samples use **PascalCase** properties (`MerchantCode`, `TerminalID`, `Charginginformation`). A camelCase naming policy alone will not produce the wire format — `Charginginformation` must serialise to `charginginformation` and `TerminalID` to `terminalID`. Apply explicit `[JsonPropertyName]` attributes on both.
- The two verbatim notes flagged inline also apply: the HttpClient sample's `await using` against an `IDisposable` class, and the Refit sample's undeclared `username` / `password`, missing `using` directives, and default `Bearer` scheme where `Basic` is required.

### Note 9 — Canonical JSON keys and their irregular casing

The wire format is what matters, whatever your language's naming conventions are:

```json
{
  "clientCorrelator": "",
  "notifyUrl": "",
  "referenceCode": "",
  "tranType": "",
  "endUserId": "",
  "remarks": "",
  "transactionOperationStatus": "",
  "originalEcocashReference": "",
  "currencyCode": "",
  "paymentAmount": {
    "charginginformation": {
      "amount": "",
      "currency": "",
      "description": ""
    },
    "chargeMetaData": {
      "channel": ""
    }
  },
  "merchantCode": "",
  "merchantPin": "",
  "merchantNumber": "",
  "countryCode": "",
  "terminalID": "",
  "location": "",
  "superMerchantName": "",
  "merchantName": ""
}
```

Three keys break camelCase and are the most common source of silent serialisation failures:

| Key | Irregularity |
|---|---|
| `charginginformation` | Entirely lowercase — **not** `chargingInformation` |
| `terminalID` | Capital `ID` — **not** `terminalId` |
| `chargeMetaData` | Capital `M` and `D` — **not** `chargeMetadata` |

`originalEcocashReference` and `currencyCode` appear only in refund payloads; `notifyUrl` and `transactionOperationStatus` appear only in payment payloads.

### Note 10 — Choosing a variant

| If you need… | Use |
|---|---|
| Spring Boot, reactive or blocking | Java WebClient |
| Spring Boot 6.1+, synchronous, modern API | Java RestClient |
| Spring Cloud, declarative interfaces | Java Feign Client |
| Laravel, idiomatic and testable (`Http::fake()`) | PHP Http Facade |
| PHP without Laravel | PHP Guzzle or Symfony Http |
| Node.js, broadest ecosystem support | Axios |
| Node.js 18+, no dependencies | Fetch API |
| Node.js, retries and hooks built in | Got |
| .NET, no extra packages | HttpClient |
| .NET, terse request building | RestSharp |
| .NET, strongly-typed declarative client | Refit |
| Python, synchronous scripts and workers | Requests |
| Python, one client for sync and async | HTTPX |
| Python, fully asynchronous services | aiohttp |

**A final caution on `clientCorrelator`.** The samples are inconsistent. The Java WebClient and RestClient, PHP, JavaScript, C# HttpClient and RestSharp, and Python samples hard-code `"REF-001"` (and `"REFUND-001"`). The Java Feign and C# Refit samples generate a timestamp-based value (`"REF-" + System.currentTimeMillis()`, `$"REF-{DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()}"`). The SDK tab does not say what happens when a correlator is reused. Generate a unique correlator per attempt, as the Feign and Refit samples do, and persist it against your own order record. The status call needs it together with `endUserId`.

### Note 11 — Verification log

Re-checked against the live **SDKs & Codegen** tab on 21 September 2026 (EcoCash Instant Payment, signed in):

| Check | Result |
|---|---|
| Code panels (5 languages × 3 variants × 5 steps) | **75 / 75 match**, compared as whitespace-insensitive SHA-256. |
| Section labels, variant names and taglines, Base URL line, Key Endpoints panel | Match. |
| Page heading | **SDKs & Code Examples** (tab name: *SDKs & Codegen*). |

**Revision history**
- **21 Sep 2026 (b):**
  - Scope restricted to the SDKs & Codegen tab as the only source of truth.
  - Removed all comparisons with the Documentation tab, the API Playground and the product Authentication tab.
  - Rewrote Notes 1–4 and the `clientCorrelator` caution from SDK-tab evidence only.
  - Removed `status` from the defensive parser in Note 2.
- **21 Sep 2026 (a):**
  - The C# install panels now use `# appsettings.json` as the portal does.
  - Added the JavaScript / Python **HTTP CLIENT** labels and the page heading.
  - Note 5: Refit downgraded to Low risk; aiohttp reason reworded.
  - Fixed 11 broken Contents links.

---

*Captured solely from the EcoCash Developer Portal → EcoCash Instant Payment (Sandbox Simulation) → **SDKs & Codegen** tab: all 5 languages and all 15 client variants, 5 steps each (75 code panels). All code is reproduced verbatim from the portal; indentation was restored where the portal's rendered text flattened it, and multi-artefact install panels were split into separate fenced blocks by language. All review commentary is confined to clearly marked notes and is not portal content. Last verified 21 September 2026 (Note 11).*
