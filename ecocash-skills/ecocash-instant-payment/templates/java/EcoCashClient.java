package com.example.ecocash;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class EcoCashClient {

    private static final ParameterizedTypeReference<Map<String, Object>> JSON =
            new ParameterizedTypeReference<>() {};

    private final RestClient http;
    private final Map<String, Object> merchant = new LinkedHashMap<>();
    private final String channel;
    private final String refundTranType;

    public EcoCashClient(
            @Value("${eip.base-url}") String baseUrl,
            @Value("${eip.username}") String username,
            @Value("${eip.password}") String password,
            @Value("${eip.merchant-code}") String merchantCode,
            @Value("${eip.merchant-pin}") String merchantPin,
            @Value("${eip.merchant-number}") String merchantNumber,
            @Value("${eip.terminal-id}") String terminalId,
            @Value("${eip.merchant-name}") String merchantName,
            @Value("${eip.super-merchant-name}") String superMerchantName,
            @Value("${eip.location}") String location,
            @Value("${eip.channel}") String channel,
            @Value("${eip.refund-tran-type}") String refundTranType) {

        this.http = RestClient.builder()
                .baseUrl(baseUrl.replaceAll("/+$", ""))
                .defaultHeaders(h -> {
                    h.setBasicAuth(username, password);
                    h.setContentType(MediaType.APPLICATION_JSON);
                    h.setAccept(java.util.List.of(MediaType.APPLICATION_JSON));
                })
                .build();
        merchant.put("merchantCode", merchantCode);
        merchant.put("merchantPin", merchantPin);
        merchant.put("merchantNumber", merchantNumber);
        merchant.put("countryCode", "ZW");
        merchant.put("terminalID", terminalId);
        merchant.put("location", location);
        merchant.put("superMerchantName", superMerchantName);
        merchant.put("merchantName", merchantName);
        this.channel = channel;
        this.refundTranType = refundTranType;
    }

    private Map<String, Object> paymentAmount(BigDecimal amount, String currency, String description) {
        Map<String, Object> info = new LinkedHashMap<>();
        info.put("amount", amount.setScale(2, RoundingMode.HALF_UP).toPlainString()); // "2.00" - section 4.5
        info.put("currency", currency);
        info.put("description", description);
        return Map.of("charginginformation", info, "chargeMetaData", Map.of("channel", channel));
    }

    /** Start a charge. Persist the correlator BEFORE calling this. */
    public Map<String, Object> charge(String msisdn, BigDecimal amount, String currency,
                                      String reference, String correlator, String notifyUrl) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("clientCorrelator", correlator);
        body.put("notifyUrl", notifyUrl == null ? "" : notifyUrl);
        body.put("referenceCode", reference);
        body.put("tranType", "MER");
        body.put("endUserId", msisdn);
        body.put("remarks", reference);
        body.put("transactionOperationStatus", "Charged");
        body.put("paymentAmount", paymentAmount(amount, currency, reference));
        body.putAll(merchant);
        return http.post().uri("/transactions/amount/").body(body).retrieve().body(JSON);
    }

    public Map<String, Object> lookup(String msisdn, String correlator) {
        return http.get()
                .uri("/{endUserId}/transactions/amount/{clientCorrelator}", msisdn, correlator)
                .retrieve().body(JSON);
    }

    public Map<String, Object> refund(String msisdn, String originalReference, BigDecimal amount,
                                      String currency, String reference) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("clientCorrelator", UUID.randomUUID().toString()); // a NEW correlator
        body.put("referenceCode", reference);
        body.put("tranType", refundTranType);
        body.put("endUserId", msisdn);
        body.put("originalEcocashReference", originalReference);
        body.put("remarks", reference);
        body.put("paymentAmount", paymentAmount(amount, currency, "Refund"));
        body.putAll(merchant);
        return http.post().uri("/transactions/refund/").body(body).retrieve().body(JSON);
    }

    /** `status` is documented; the portal's SDK samples read two other names. */
    public static String statusOf(Map<String, Object> b) {
        for (String k : new String[] {"status", "transactionStatus", "transactionOperationStatus"}) {
            if (b != null && b.get(k) != null) return b.get(k).toString();
        }
        return null;
    }

    public static String referenceOf(Map<String, Object> b) {
        Object v = b.get("ecocashReference") != null ? b.get("ecocashReference") : b.get("transactionId");
        return v == null ? null : v.toString();
    }
}
