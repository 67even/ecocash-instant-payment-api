using System.Globalization;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json.Nodes;

public sealed class EcoCashClient
{
    private readonly HttpClient _http;
    private readonly Dictionary<string, string> _cfg;

    public EcoCashClient(HttpClient http, Dictionary<string, string> cfg)
    {
        _cfg = cfg;
        _http = http;
        _http.BaseAddress = new Uri(cfg["EIP_BASE_URL"].TrimEnd('/') + "/");
        var token = Convert.ToBase64String(
            Encoding.UTF8.GetBytes($"{cfg["EIP_USERNAME"]}:{cfg["EIP_PASSWORD"]}"));
        _http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Basic", token);
        _http.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
        _http.Timeout = TimeSpan.FromSeconds(30);
    }

    private JsonObject Body(string correlator, string tranType, string msisdn, decimal amount,
                            string currency, string reference, string description)
    {
        return new JsonObject
        {
            ["clientCorrelator"] = correlator,
            ["referenceCode"] = reference,
            ["tranType"] = tranType,
            ["endUserId"] = msisdn,
            ["remarks"] = reference,
            ["paymentAmount"] = new JsonObject
            {
                ["charginginformation"] = new JsonObject
                {
                    ["amount"] = amount.ToString("0.00", CultureInfo.InvariantCulture), // "2.00" - section 4.5
                    ["currency"] = currency,
                    ["description"] = description,
                },
                ["chargeMetaData"] = new JsonObject { ["channel"] = _cfg["EIP_CHANNEL"] },
            },
            ["merchantCode"] = _cfg["EIP_MERCHANT_CODE"],
            ["merchantPin"] = _cfg["EIP_MERCHANT_PIN"],
            ["merchantNumber"] = _cfg["EIP_MERCHANT_NUMBER"],
            ["countryCode"] = "ZW",
            ["terminalID"] = _cfg["EIP_TERMINAL_ID"],
            ["location"] = _cfg["EIP_LOCATION"],
            ["superMerchantName"] = _cfg["EIP_SUPER_MERCHANT_NAME"],
            ["merchantName"] = _cfg["EIP_MERCHANT_NAME"],
        };
    }

    /// <summary>Start a charge. Persist the correlator BEFORE calling this.</summary>
    public Task<JsonObject> ChargeAsync(string msisdn, decimal amount, string currency,
                                        string reference, string correlator, string notifyUrl = "")
    {
        var body = Body(correlator, "MER", msisdn, amount, currency, reference, reference);
        body["notifyUrl"] = notifyUrl;
        body["transactionOperationStatus"] = "Charged";
        return SendAsync(HttpMethod.Post, "transactions/amount/", body);
    }

    public Task<JsonObject> LookupAsync(string msisdn, string correlator) =>
        SendAsync(HttpMethod.Get,
            $"{Uri.EscapeDataString(msisdn)}/transactions/amount/{Uri.EscapeDataString(correlator)}", null);

    public Task<JsonObject> RefundAsync(string msisdn, string originalReference, decimal amount,
                                        string currency, string reference)
    {
        var body = Body(Guid.NewGuid().ToString(), _cfg["EIP_REFUND_TRAN_TYPE"], msisdn,
                        amount, currency, reference, "Refund"); // a NEW correlator
        body["originalEcocashReference"] = originalReference;
        return SendAsync(HttpMethod.Post, "transactions/refund/", body);
    }

    private async Task<JsonObject> SendAsync(HttpMethod method, string path, JsonObject? body)
    {
        using var req = new HttpRequestMessage(method, path);
        if (body is not null) req.Content = JsonContent.Create(body);
        using var res = await _http.SendAsync(req);
        var text = await res.Content.ReadAsStringAsync();
        var json = (string.IsNullOrWhiteSpace(text) ? null : JsonNode.Parse(text) as JsonObject) ?? new JsonObject();
        if (!res.IsSuccessStatusCode)
            throw new HttpRequestException(
                $"EIP {(int)res.StatusCode}: {json["statusMessage"]}", null, res.StatusCode);
        return json;
    }

    /// <summary>`status` is documented; the SDK samples read two other names.</summary>
    public static string? StatusOf(JsonObject b) =>
        (b["status"] ?? b["transactionStatus"] ?? b["transactionOperationStatus"])?.ToString();

    public static string? ReferenceOf(JsonObject b) =>
        (b["ecocashReference"] ?? b["transactionId"])?.ToString();
}
